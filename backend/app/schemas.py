"""Pydantic request/response schemas for the API layer.

Kept separate from the ORM so the wire format is explicit and stable. Medians
lead every payload; means are present but clearly labelled comparison-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class InfluencerCreate(BaseModel):
    handle: str
    platform: str
    display_name: Optional[str] = None
    follower_count: Optional[int] = None


class PullRequest(BaseModel):
    """Trigger an aggregator pull for one person (operator action)."""

    handle: str
    platform: str
    max_posts: int = 20


class EngagementFormulaIn(BaseModel):
    likes_weight: float = 1.0
    comments_weight: float = 1.0
    shares_weight: float = 1.0


class OutlierConfigIn(BaseModel):
    viral_multiple: float = 3.0
    mean_to_median_flag: float = 2.0


class RecomputeRequest(BaseModel):
    """Re-score everyone, optionally with a different engagement formula (§5)."""

    engagement_formula: Optional[EngagementFormulaIn] = None
    outlier_config: Optional[OutlierConfigIn] = None


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class MetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_count: int
    # Median — the ranking metrics.
    median_views: Optional[float] = None
    median_likes: Optional[float] = None
    median_engagement: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    # Mean — comparison only, never used for ranking.
    mean_views: Optional[float] = None
    mean_likes: Optional[float] = None
    mean_engagement: Optional[float] = None
    mean_engagement_rate: Optional[float] = None
    # Consistency / outlier signals.
    views_mean_to_median_ratio: Optional[float] = None
    viral_post_count: int = 0
    is_outlier_driven: bool = False
    computed_at: Optional[datetime] = None


class RankedRow(BaseModel):
    """One row of the ranked list screen."""

    id: int
    handle: str
    platform: str
    display_name: Optional[str] = None
    follower_count: Optional[int] = None
    tier: Optional[str] = None
    rank: int
    metrics: Optional[MetricsOut] = None


class PostOut(BaseModel):
    external_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    # Derived for display using the latest metrics' formula.
    engagement: Optional[float] = None
    engagement_rate: Optional[float] = None


class InfluencerDetail(BaseModel):
    id: int
    handle: str
    platform: str
    display_name: Optional[str] = None
    follower_count: Optional[int] = None
    tier: Optional[str] = None
    metrics: Optional[MetricsOut] = None
    posts: list[PostOut] = Field(default_factory=list)


class CompareRow(BaseModel):
    """One influencer in the side-by-side compare screen (median metrics)."""

    id: int
    handle: str
    display_name: Optional[str] = None
    tier: Optional[str] = None
    median_views: Optional[float] = None
    median_engagement: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    is_outlier_driven: bool = False
