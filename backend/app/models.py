"""ORM data model: influencers, raw posts, and computed metrics.

Design notes tied to the brief:
- **Raw post rows are stored separately from computed metrics** (§4/§6) so that
  when the engagement formula or thresholds change, metrics can be recomputed
  from the raw data without re-hitting any aggregator.
- Each `InfluencerMetrics` row snapshots the `engagement_formula` and
  `outlier_config` used, so any stored ranking is reproducible and explainable.
- Metrics are versioned (one influencer -> many metric rows over time) rather
  than overwritten, which keeps a history and leaves room for the phase-2
  media-spend model to join against point-in-time metrics (§8).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Influencer(Base):
    __tablename__ = "influencers"
    __table_args__ = (UniqueConstraint("platform", "handle", name="uq_platform_handle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    handle: Mapped[str] = mapped_column(String(255), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)  # tiktok, instagram, youtube
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    follower_count: Mapped[Optional[int]] = mapped_column(Integer)
    # 'macro' | 'micro' | 'nano' | 'unknown', derived from follower_count via TierConfig.
    tier: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    posts: Mapped[list["Post"]] = relationship(
        back_populates="influencer",
        cascade="all, delete-orphan",
        order_by="Post.posted_at.desc()",
    )
    metrics: Mapped[list["InfluencerMetrics"]] = relationship(
        back_populates="influencer",
        cascade="all, delete-orphan",
        order_by="InfluencerMetrics.computed_at.desc()",
    )


class Post(Base):
    """A single post's raw metrics as captured from an aggregator/CSV/manual entry.

    Raw signals only — no derived values are stored here; engagement and rates
    are recomputed on demand by the metric engine so a formula change never
    requires a re-pull.
    """

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("influencer_id", "external_id", name="uq_influencer_external_post"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    influencer_id: Mapped[int] = mapped_column(
        ForeignKey("influencers.id", ondelete="CASCADE"), index=True
    )
    # The aggregator's own id for the post, used to dedupe across pulls.
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

    views: Mapped[Optional[int]] = mapped_column(Integer)
    likes: Mapped[Optional[int]] = mapped_column(Integer)
    comments: Mapped[Optional[int]] = mapped_column(Integer)
    shares: Mapped[Optional[int]] = mapped_column(Integer)

    # Whatever extra fields the vendor returned, kept verbatim for auditability.
    raw: Mapped[Optional[dict]] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    influencer: Mapped["Influencer"] = relationship(back_populates="posts")


class InfluencerMetrics(Base):
    """A point-in-time computed roll-up for one influencer (median-first)."""

    __tablename__ = "influencer_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    influencer_id: Mapped[int] = mapped_column(
        ForeignKey("influencers.id", ondelete="CASCADE"), index=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), index=True
    )
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # Primary ranking metric.
    median_views: Mapped[Optional[float]] = mapped_column(Float, index=True)
    mean_views: Mapped[Optional[float]] = mapped_column(Float)

    median_likes: Mapped[Optional[float]] = mapped_column(Float)
    mean_likes: Mapped[Optional[float]] = mapped_column(Float)

    median_engagement: Mapped[Optional[float]] = mapped_column(Float)
    mean_engagement: Mapped[Optional[float]] = mapped_column(Float)

    median_engagement_rate: Mapped[Optional[float]] = mapped_column(Float)
    mean_engagement_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Consistency / outlier signals.
    views_mean_to_median_ratio: Mapped[Optional[float]] = mapped_column(Float)
    viral_post_count: Mapped[int] = mapped_column(Integer, default=0)
    is_outlier_driven: Mapped[bool] = mapped_column(default=False, index=True)

    # Snapshots of the config used, so this row is fully reproducible/explainable.
    engagement_formula: Mapped[Optional[dict]] = mapped_column(JSON)
    outlier_config: Mapped[Optional[dict]] = mapped_column(JSON)

    influencer: Mapped["Influencer"] = relationship(back_populates="metrics")
