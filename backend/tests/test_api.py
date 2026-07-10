"""API tests: ranking, detail, compare, auth gating, pull, import, recompute."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.deps import get_db
from app.main import app

OPERATOR = {"Authorization": "Bearer dev-operator-token"}


@pytest.fixture
def client():
    # StaticPool + shared connection so every session (across TestClient's
    # thread) sees the same in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    # Disable the startup init_db (it would hit the real sqlite file).
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_via_pull(client):
    for handle, platform in [
        ("steady_sam", "tiktok"),
        ("viral_vince", "tiktok"),
        ("micro_mia", "instagram"),
    ]:
        r = client.post(
            "/influencers/pull",
            json={"handle": handle, "platform": platform},
            headers=OPERATOR,
        )
        assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# Auth gating
# --------------------------------------------------------------------------- #
def test_write_requires_operator(client):
    r = client.post("/influencers/pull", json={"handle": "x", "platform": "tiktok"})
    assert r.status_code == 403


def test_read_is_open_to_clients(client):
    assert client.get("/influencers").status_code == 200


# --------------------------------------------------------------------------- #
# Ranking (the primary screen)
# --------------------------------------------------------------------------- #
def test_ranked_list_defaults_to_median_views(client):
    _seed_via_pull(client)
    rows = client.get("/influencers").json()
    handles = [r["handle"] for r in rows]
    # Steady Sam (median ~200k) ranks above Viral Vince (median 0) despite
    # Vince's inflated mean. Ranks are 1-indexed and ordered.
    assert handles.index("steady_sam") < handles.index("viral_vince")
    assert rows[0]["rank"] == 1
    assert rows[-1]["handle"] == "viral_vince"
    assert rows[-1]["metrics"]["median_views"] == 0
    assert rows[-1]["metrics"]["is_outlier_driven"] is True


def test_average_is_not_a_valid_sort_key(client):
    _seed_via_pull(client)
    r = client.get("/influencers", params={"sort_by": "mean_views"})
    assert r.status_code == 400


def test_tier_filter(client):
    _seed_via_pull(client)
    rows = client.get("/influencers", params={"tier": "micro"}).json()
    assert {r["handle"] for r in rows} == {"micro_mia"}


# --------------------------------------------------------------------------- #
# Detail + compare
# --------------------------------------------------------------------------- #
def test_influencer_detail_has_posts_and_median_vs_mean(client):
    _seed_via_pull(client)
    vince_id = next(
        r["id"] for r in client.get("/influencers").json() if r["handle"] == "viral_vince"
    )
    detail = client.get(f"/influencers/{vince_id}").json()
    assert detail["metrics"]["median_views"] == 0
    assert detail["metrics"]["mean_views"] == 100_000  # comparison figure present
    assert len(detail["posts"]) == 10
    # per-post engagement is derived for the detail table
    assert any(p["engagement"] is not None for p in detail["posts"])


def test_compare_returns_median_metrics(client):
    _seed_via_pull(client)
    ids = ",".join(str(r["id"]) for r in client.get("/influencers").json())
    rows = client.get("/influencers/compare", params={"ids": ids}).json()
    assert len(rows) == 3
    assert all("median_views" in r for r in rows)


def test_detail_404(client):
    assert client.get("/influencers/999").status_code == 404


# --------------------------------------------------------------------------- #
# Operator actions
# --------------------------------------------------------------------------- #
def test_create_and_duplicate_conflict(client):
    body = {"handle": "new_nick", "platform": "tiktok", "follower_count": 250000}
    r = client.post("/influencers", json=body, headers=OPERATOR)
    assert r.status_code == 201
    assert r.json()["tier"] == "macro"
    assert client.post("/influencers", json=body, headers=OPERATOR).status_code == 409


def test_csv_import(client):
    csv_text = (
        "platform,handle,display_name,follower_count,external_id,posted_at,views,likes,comments,shares\n"
        "tiktok,csv_carol,CSV Carol,50000,c1,2026-06-30,10000,500,50,20\n"
        "tiktok,csv_carol,CSV Carol,50000,c2,2026-06-28,12000,600,60,25\n"
    )
    r = client.post(
        "/import/csv",
        files={"file": ("posts.csv", csv_text, "text/csv")},
        headers=OPERATOR,
    )
    assert r.status_code == 200
    assert r.json()["ingested"] == 1
    assert any(row["handle"] == "csv_carol" for row in client.get("/influencers").json())


def test_recompute_with_custom_formula(client):
    _seed_via_pull(client)
    r = client.post(
        "/recompute",
        json={"engagement_formula": {"likes_weight": 2, "comments_weight": 3, "shares_weight": 1}},
        headers=OPERATOR,
    )
    assert r.status_code == 200
    assert r.json()["recomputed"] == 3


def test_export_ranked_csv(client):
    _seed_via_pull(client)
    r = client.get("/export/ranked.csv", headers=OPERATOR)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "median_views" in r.text
    assert "viral_vince" in r.text
