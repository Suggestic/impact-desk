"""End-to-end: aggregator -> ingest -> DB -> recomputed metrics.

Uses an in-memory SQLite DB so the full data path is exercised without touching
the developer's real database file.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.aggregator import CSVAggregatorClient, MockAggregatorClient
from app.db import Base
from app.ingest import ingest_profile, pull_and_ingest
from app.models import Influencer, Post
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sample_posts.csv"


@pytest.fixture
def session():
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    s = Session()
    yield s
    s.close()


def test_pull_and_ingest_computes_median_first_metrics(session):
    # The mock's viral archetype must land as median 0 / mean 100k / flagged.
    inf = pull_and_ingest(session, "viral_vince", "tiktok", client=MockAggregatorClient())
    metrics = inf.metrics[0]
    assert metrics.median_views == 0
    assert metrics.mean_views == 100_000
    assert metrics.is_outlier_driven is True
    assert inf.tier == "macro"  # 120k followers -> macro, yet median exposes it


def test_ingest_is_idempotent_on_repull(session):
    client = MockAggregatorClient()
    pull_and_ingest(session, "steady_sam", "tiktok", client=client)
    pull_and_ingest(session, "steady_sam", "tiktok", client=client)  # re-pull

    influencers = session.query(Influencer).all()
    assert len(influencers) == 1              # not duplicated
    assert len(influencers[0].posts) == 12    # posts upserted, not doubled
    assert len(influencers[0].metrics) == 2   # metrics history versioned


def test_ingest_from_csv_handles_missing_metrics(session):
    client = CSVAggregatorClient.from_path(FIXTURE)
    inf = ingest_profile(session, client.fetch_profile("partial_pat", "instagram"))
    posts = {p.external_id: p for p in inf.posts}
    assert posts["p1"].likes is None
    assert posts["p2"].views is None
    # metrics still compute despite the gaps
    assert inf.metrics[0].post_count == 2


def test_csv_faux_account_flagged_over_honest_one(session):
    client = CSVAggregatorClient.from_path(FIXTURE)
    faux = ingest_profile(session, client.fetch_profile("faux_fred", "tiktok"))
    hana = ingest_profile(session, client.fetch_profile("honest_hana", "tiktok"))

    assert faux.metrics[0].is_outlier_driven is True
    assert hana.metrics[0].is_outlier_driven is False
    # Honest Hana's *median* beats Faux Fred's despite far fewer followers.
    assert hana.metrics[0].median_views > faux.metrics[0].median_views
