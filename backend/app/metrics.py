"""Median-first metric engine for influencer impact ranking.

This module is the heart of the product. The operator's core insight is that
**averages lie**: an account with 9 zero-view posts and 1 viral post averages
100k views but is not a real influencer. We therefore rank by the **median**,
which is robust to viral outliers, and expose mean values only for comparison.

Everything here is pure and ORM-free: functions take plain values / dataclasses
and return a `ComputedMetrics`. This keeps the median logic trivially unit
testable (see tests/test_metrics.py) and lets the persistence layer stay dumb.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median
from typing import Optional, Sequence

Number = Optional[float]


# --------------------------------------------------------------------------- #
# Configuration (both are persisted alongside computed metrics so a stored
# result can always be reproduced / explained, per the brief's §4 + §8).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EngagementFormula:
    """How a single post's engagement is composed from its raw signals.

    engagement = likes*likes_weight + comments*comments_weight + shares*shares_weight

    The formula is explicit and configurable because the exact definition the
    operator wants is an open item (§8); different aggregators also expose
    different signals. A `None` component is treated as 0, but a post whose
    signals are *all* missing yields `None` (i.e. "no data", not "zero
    engagement") so it can be excluded from aggregation rather than dragging
    the median down.
    """

    likes_weight: float = 1.0
    comments_weight: float = 1.0
    shares_weight: float = 1.0

    def compute(
        self,
        likes: Optional[int],
        comments: Optional[int],
        shares: Optional[int],
    ) -> Number:
        if likes is None and comments is None and shares is None:
            return None
        return (
            (likes or 0) * self.likes_weight
            + (comments or 0) * self.comments_weight
            + (shares or 0) * self.shares_weight
        )

    def as_dict(self) -> dict:
        return {
            "likes_weight": self.likes_weight,
            "comments_weight": self.comments_weight,
            "shares_weight": self.shares_weight,
        }


@dataclass(frozen=True)
class OutlierConfig:
    """Thresholds for the "who's real?" consistency flags."""

    # A post counts as "viral" if its views exceed this multiple of the
    # median. When the median is 0, any post with views > 0 is viral.
    viral_multiple: float = 3.0
    # If mean views are at least this many times the median, the account's
    # reach is judged to be carried by a few outliers.
    mean_to_median_flag: float = 2.0

    def as_dict(self) -> dict:
        return {
            "viral_multiple": self.viral_multiple,
            "mean_to_median_flag": self.mean_to_median_flag,
        }


# --------------------------------------------------------------------------- #
# Inputs / outputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PostMetricsInput:
    """The raw per-post numbers pulled from an aggregator (or CSV/manual entry).

    Any field may be `None` to represent a metric the source did not provide;
    the engine excludes missing values per-metric rather than treating them as 0.
    """

    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None


@dataclass
class ComputedMetrics:
    """Per-influencer roll-up. Medians are primary; means are comparison-only."""

    post_count: int = 0

    # Primary ranking metric first.
    median_views: Number = None
    mean_views: Number = None

    median_likes: Number = None
    mean_likes: Number = None

    median_engagement: Number = None
    mean_engagement: Number = None

    # median of per-post (engagement / views); divide-by-zero guarded.
    median_engagement_rate: Number = None
    mean_engagement_rate: Number = None

    # Consistency / outlier signals — the "who's real" story.
    views_mean_to_median_ratio: Number = None
    viral_post_count: int = 0
    is_outlier_driven: bool = False

    def as_dict(self) -> dict:
        return {
            "post_count": self.post_count,
            "median_views": self.median_views,
            "mean_views": self.mean_views,
            "median_likes": self.median_likes,
            "mean_likes": self.mean_likes,
            "median_engagement": self.median_engagement,
            "mean_engagement": self.mean_engagement,
            "median_engagement_rate": self.median_engagement_rate,
            "mean_engagement_rate": self.mean_engagement_rate,
            "views_mean_to_median_ratio": self.views_mean_to_median_ratio,
            "viral_post_count": self.viral_post_count,
            "is_outlier_driven": self.is_outlier_driven,
        }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _present(values: Sequence[Optional[float]]) -> list[float]:
    """Drop `None`s — a missing metric must not be counted as zero."""
    return [float(v) for v in values if v is not None]


def _median(values: Sequence[Optional[float]]) -> Number:
    present = _present(values)
    return float(median(present)) if present else None


def _mean(values: Sequence[Optional[float]]) -> Number:
    present = _present(values)
    return float(mean(present)) if present else None


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #
def compute_metrics(
    posts: Sequence[PostMetricsInput],
    *,
    engagement_formula: EngagementFormula = EngagementFormula(),
    outlier_config: OutlierConfig = OutlierConfig(),
    max_posts: Optional[int] = 20,
) -> ComputedMetrics:
    """Roll a list of posts up into median-first influencer metrics.

    Only the most recent `max_posts` are considered (the brief specifies the
    last 20). Callers should pass posts already ordered newest-first; pass
    `max_posts=None` to use everything. Influencers with fewer than `max_posts`
    posts are handled naturally — we use what's available and report the count.
    """
    if max_posts is not None:
        posts = list(posts)[:max_posts]

    result = ComputedMetrics(post_count=len(posts))
    if not posts:
        return result

    views = [p.views for p in posts]
    likes = [p.likes for p in posts]
    engagements = [
        engagement_formula.compute(p.likes, p.comments, p.shares) for p in posts
    ]

    # Per-post engagement rate, guarding divide-by-zero and missing views:
    # a post with 0 or missing views contributes no rate rather than infinity.
    rates = [
        eng / v
        for p, eng in zip(posts, engagements)
        for v in (p.views,)
        if v is not None and v > 0 and eng is not None
    ]

    result.median_views = _median(views)
    result.mean_views = _mean(views)
    result.median_likes = _median(likes)
    result.mean_likes = _mean(likes)
    result.median_engagement = _median(engagements)
    result.mean_engagement = _mean(engagements)
    result.median_engagement_rate = float(median(rates)) if rates else None
    result.mean_engagement_rate = float(mean(rates)) if rates else None

    _apply_outlier_flags(result, _present(views), outlier_config)
    return result


def _apply_outlier_flags(
    result: ComputedMetrics,
    views_present: list[float],
    cfg: OutlierConfig,
) -> None:
    med, avg = result.median_views, result.mean_views
    if med is None or avg is None:
        return

    if med > 0:
        result.views_mean_to_median_ratio = avg / med
        result.viral_post_count = sum(
            1 for v in views_present if v > cfg.viral_multiple * med
        )
        result.is_outlier_driven = (avg / med) >= cfg.mean_to_median_flag
    else:
        # Median is 0 — the "9 zeros + 1 viral" shape. Ratio is undefined
        # (leave as None), but any post with views is itself the outlier, and
        # a positive mean over a zero median is the strongest possible signal
        # that reach is outlier-driven.
        result.viral_post_count = sum(1 for v in views_present if v > 0)
        result.is_outlier_driven = avg > 0
