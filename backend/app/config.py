"""Application-level configuration and defaults.

Aggregator vendor selection is deliberately absent here — data access lives
behind the (forthcoming) `AggregatorClient` interface, and no vendor is
hardcoded (§3/§8). This file holds only the knobs the operator can tune:
the engagement formula, outlier thresholds, and the macro/micro tier split.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .metrics import EngagementFormula, OutlierConfig

# SQLite for the prototype; set DATABASE_URL to a Supabase/Postgres URL in prod.
# e.g. postgresql+psycopg://user:pass@host:5432/postgres
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL", "sqlite:///./influencer_rank.db"
)

# The number of most-recent posts to score per influencer (§4).
POSTS_PER_INFLUENCER: int = int(os.environ.get("POSTS_PER_INFLUENCER", "20"))

# Default scoring config. The exact engagement formula and thresholds are open
# items (§8); these are sensible starting points and are overridable per run.
DEFAULT_ENGAGEMENT_FORMULA = EngagementFormula(
    likes_weight=1.0, comments_weight=1.0, shares_weight=1.0
)
DEFAULT_OUTLIER_CONFIG = OutlierConfig(viral_multiple=3.0, mean_to_median_flag=2.0)


@dataclass(frozen=True)
class TierConfig:
    """Configurable macro/micro follower-count split (the call opened on this).

    Anyone at or above `macro_min_followers` is 'macro'; below is 'micro'.
    A three-way split point is included so the UI can offer nano/micro/macro
    later without a schema change.
    """

    micro_min_followers: int = 10_000
    macro_min_followers: int = 100_000

    def classify(self, follower_count: int | None) -> str:
        if follower_count is None:
            return "unknown"
        if follower_count >= self.macro_min_followers:
            return "macro"
        if follower_count >= self.micro_min_followers:
            return "micro"
        return "nano"


DEFAULT_TIER_CONFIG = TierConfig()
