"""Bridge between the ORM and the pure metric engine.

The engine (metrics.py) knows nothing about the database. This module adapts
stored `Post` rows into `PostMetricsInput`, runs the engine, and persists an
`InfluencerMetrics` snapshot. Recomputation with a new formula is just calling
`recompute_for_influencer` again — no aggregator round-trip.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import (
    DEFAULT_ENGAGEMENT_FORMULA,
    DEFAULT_OUTLIER_CONFIG,
    DEFAULT_TIER_CONFIG,
    POSTS_PER_INFLUENCER,
)
from .metrics import (
    EngagementFormula,
    OutlierConfig,
    PostMetricsInput,
    compute_metrics,
)
from .models import Influencer, InfluencerMetrics, Post


def _to_inputs(posts: list[Post]) -> list[PostMetricsInput]:
    return [
        PostMetricsInput(views=p.views, likes=p.likes, comments=p.comments, shares=p.shares)
        for p in posts
    ]


def recompute_for_influencer(
    session: Session,
    influencer: Influencer,
    *,
    engagement_formula: EngagementFormula = DEFAULT_ENGAGEMENT_FORMULA,
    outlier_config: OutlierConfig = DEFAULT_OUTLIER_CONFIG,
    max_posts: int = POSTS_PER_INFLUENCER,
) -> InfluencerMetrics:
    """Compute and persist a fresh metrics snapshot for one influencer.

    Posts are ordered newest-first (relationship default) so `max_posts` keeps
    the most recent N. Also refreshes the follower tier.
    """
    computed = compute_metrics(
        _to_inputs(influencer.posts),
        engagement_formula=engagement_formula,
        outlier_config=outlier_config,
        max_posts=max_posts,
    )

    influencer.tier = DEFAULT_TIER_CONFIG.classify(influencer.follower_count)

    row = InfluencerMetrics(
        influencer_id=influencer.id,
        engagement_formula=engagement_formula.as_dict(),
        outlier_config=outlier_config.as_dict(),
        **computed.as_dict(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def recompute_all(session: Session, **kwargs) -> list[InfluencerMetrics]:
    influencers = session.scalars(select(Influencer)).all()
    return [recompute_for_influencer(session, inf, **kwargs) for inf in influencers]


def latest_metrics(influencer: Influencer) -> InfluencerMetrics | None:
    """Most recent computed snapshot for an influencer (None if never scored)."""
    return influencer.metrics[0] if influencer.metrics else None


def formula_from_snapshot(snapshot: dict | None) -> EngagementFormula:
    """Rebuild the engagement formula a metrics row was computed with."""
    if not snapshot:
        return DEFAULT_ENGAGEMENT_FORMULA
    return EngagementFormula(
        likes_weight=snapshot.get("likes_weight", 1.0),
        comments_weight=snapshot.get("comments_weight", 1.0),
        shares_weight=snapshot.get("shares_weight", 1.0),
    )
