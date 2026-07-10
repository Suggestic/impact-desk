"""Ingestion: land an `AggregatedProfile` into the DB, then recompute metrics.

This is the only place that maps aggregator transfer objects onto ORM rows, so
adapters stay database-free. Influencers and posts are **upserted** (idempotent)
by their natural keys — re-pulling the same profile updates in place rather than
duplicating, which is what a repeated "trigger a data pull" should do.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .aggregator import AggregatorClient, get_client
from .aggregator.base import AggregatedProfile
from .config import DEFAULT_TIER_CONFIG
from .models import Influencer, Post
from .service import recompute_for_influencer


def ingest_profile(
    session: Session,
    profile: AggregatedProfile,
    *,
    recompute: bool = True,
    **recompute_kwargs,
) -> Influencer:
    """Upsert one profile (and its posts) and optionally recompute its metrics."""
    influencer = (
        session.query(Influencer)
        .filter_by(platform=profile.platform, handle=profile.handle)
        .first()
    )
    if influencer is None:
        influencer = Influencer(handle=profile.handle, platform=profile.platform)
        session.add(influencer)

    influencer.display_name = profile.display_name or influencer.display_name
    influencer.follower_count = profile.follower_count
    influencer.tier = DEFAULT_TIER_CONFIG.classify(profile.follower_count)

    session.flush()  # ensure influencer.id for post FKs

    # Index existing posts by external_id (falling back to a positional key when
    # a source provides no id) so re-pulls update rather than duplicate.
    existing = {p.external_id: p for p in influencer.posts if p.external_id is not None}
    for idx, ap in enumerate(profile.posts):
        key = ap.external_id if ap.external_id is not None else f"__pos_{idx}"
        post = existing.get(key)
        if post is None:
            post = Post(influencer_id=influencer.id, external_id=key)
            session.add(post)
            influencer.posts.append(post)
        post.posted_at = ap.posted_at
        post.views = ap.views
        post.likes = ap.likes
        post.comments = ap.comments
        post.shares = ap.shares
        post.raw = ap.raw or None

    session.commit()
    if recompute:
        recompute_for_influencer(session, influencer, **recompute_kwargs)
    return influencer


def pull_and_ingest(
    session: Session,
    handle: str,
    platform: str,
    *,
    client: AggregatorClient | None = None,
    max_posts: int = 20,
    **recompute_kwargs,
) -> Influencer:
    """High-level 'trigger a data pull for this person' used by the operator view.

    Uses the configured aggregator (mock by default) unless a client is passed.
    """
    client = client or get_client()
    profile = client.fetch_profile(handle, platform, max_posts=max_posts)
    return ingest_profile(session, profile, max_posts=max_posts, **recompute_kwargs)
