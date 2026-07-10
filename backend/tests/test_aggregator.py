"""Tests for the AggregatorClient interface and its mock + CSV adapters."""

from pathlib import Path

import pytest

from app.aggregator import (
    AggregatorClient,
    CSVAggregatorClient,
    MockAggregatorClient,
    ProfileNotFound,
    get_client,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_posts.csv"


# --------------------------------------------------------------------------- #
# Interface / factory
# --------------------------------------------------------------------------- #
def test_factory_returns_mock_by_default():
    client = get_client()
    assert isinstance(client, MockAggregatorClient)
    assert isinstance(client, AggregatorClient)
    assert client.name == "mock"


def test_factory_rejects_unknown_vendor():
    with pytest.raises(ValueError):
        get_client("definitely_not_a_vendor")


def test_csv_factory_requires_path():
    with pytest.raises(ValueError):
        get_client("csv")


# --------------------------------------------------------------------------- #
# Mock adapter
# --------------------------------------------------------------------------- #
def test_mock_serves_hand_authored_outlier_archetype():
    profile = MockAggregatorClient().fetch_profile("viral_vince", "tiktok")
    assert profile.display_name == "Viral Vince"
    assert len(profile.posts) == 10
    assert max(p.views for p in profile.posts) == 1_000_000
    assert sum(1 for p in profile.posts if p.views == 0) == 9


def test_mock_generates_deterministic_data_for_unknown_handle():
    a = MockAggregatorClient().fetch_profile("random_rita", "youtube")
    b = MockAggregatorClient().fetch_profile("random_rita", "youtube")
    assert a.follower_count == b.follower_count
    assert [p.views for p in a.posts] == [p.views for p in b.posts]
    assert len(a.posts) == 20  # default max


def test_mock_respects_max_posts():
    profile = MockAggregatorClient().fetch_profile("random_rita", "youtube", max_posts=5)
    assert len(profile.posts) == 5


def test_mock_never_raises_for_arbitrary_handle():
    # Any handle "works" for the mock, so the app is runnable with no vendor.
    profile = MockAggregatorClient().fetch_profile("nobody_special", "tiktok")
    assert profile.handle == "nobody_special"
    assert profile.posts


# --------------------------------------------------------------------------- #
# CSV / manual adapter
# --------------------------------------------------------------------------- #
def test_csv_groups_rows_into_profiles():
    client = CSVAggregatorClient.from_path(FIXTURE)
    hana = client.fetch_profile("honest_hana", "tiktok")
    assert hana.display_name == "Honest Hana"
    assert hana.follower_count == 410_000
    assert len(hana.posts) == 4


def test_csv_orders_posts_newest_first():
    client = CSVAggregatorClient.from_path(FIXTURE)
    hana = client.fetch_profile("honest_hana", "tiktok")
    dates = [p.posted_at for p in hana.posts]
    assert dates == sorted(dates, reverse=True)


def test_csv_blank_numeric_cells_become_none_not_zero():
    client = CSVAggregatorClient.from_path(FIXTURE)
    pat = client.fetch_profile("partial_pat", "instagram")
    by_id = {p.external_id: p for p in pat.posts}
    assert by_id["p1"].likes is None      # blank likes -> missing, not 0
    assert by_id["p1"].views == 8000
    assert by_id["p2"].views is None      # blank views -> missing


def test_csv_raises_for_absent_profile():
    client = CSVAggregatorClient.from_path(FIXTURE)
    with pytest.raises(ProfileNotFound):
        client.fetch_profile("ghost", "tiktok")


def test_csv_from_rows_supports_manual_entry():
    rows = [
        {"platform": "tiktok", "handle": "typed_tim", "display_name": "Typed Tim",
         "follower_count": "5000", "external_id": "t1", "posted_at": "2026-06-30",
         "views": "1000", "likes": "50", "comments": "5", "shares": "2"},
    ]
    client = CSVAggregatorClient.from_rows(rows)
    tim = client.fetch_profile("typed_tim", "tiktok")
    assert tim.posts[0].views == 1000


def test_csv_preserves_extra_columns_in_raw():
    rows = [
        {"platform": "x", "handle": "h", "external_id": "1", "views": "10",
         "campaign": "summer-2026"},
    ]
    client = CSVAggregatorClient.from_rows(rows)
    post = client.fetch_profile("h", "x").posts[0]
    assert post.raw.get("campaign") == "summer-2026"


def test_fetch_profiles_skips_missing_in_batch():
    client = CSVAggregatorClient.from_path(FIXTURE)
    got = client.fetch_profiles([("honest_hana", "tiktok"), ("ghost", "tiktok")])
    assert len(got) == 1
    assert got[0].handle == "honest_hana"
