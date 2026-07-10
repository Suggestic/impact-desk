"""The single seam through which *all* external influencer data flows.

Per the brief (§3): direct scraping is off the table, the concrete vendor is an
unresolved business decision, and the code must make swapping vendors trivial.
So every data source — the mock, CSV/manual entry, or a future paid aggregator
(Modash, CreatorDB, …) — implements this one `AggregatorClient` interface, and
nothing downstream knows or cares which one is wired in.

The transfer objects here are intentionally decoupled from the ORM models so an
adapter never imports the database. `app/ingest.py` maps these into rows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional


class ProfileNotFound(LookupError):
    """Raised when an adapter has no data for the requested handle/platform."""


@dataclass(frozen=True)
class AggregatedPost:
    """One post's raw signals as reported by a source. Any field may be None."""

    external_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    # Anything extra the source returned, kept verbatim for auditability.
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AggregatedProfile:
    """A profile plus its recent posts, newest-first."""

    handle: str
    platform: str
    display_name: Optional[str] = None
    follower_count: Optional[int] = None
    posts: list[AggregatedPost] = field(default_factory=list)


class AggregatorClient(ABC):
    """Vendor-agnostic contract. Swap implementations without touching callers."""

    #: Human-readable source name, surfaced in the UI / audit ("mock", "csv", …).
    name: str = "abstract"

    @abstractmethod
    def fetch_profile(
        self, handle: str, platform: str, *, max_posts: int = 20
    ) -> AggregatedProfile:
        """Return the profile and its most-recent posts (newest-first).

        Raises `ProfileNotFound` if the source has no data for this handle.
        """
        raise NotImplementedError

    def fetch_profiles(
        self, handles: Iterable[tuple[str, str]], *, max_posts: int = 20
    ) -> list[AggregatedProfile]:
        """Convenience batch fetch over (handle, platform) pairs.

        Missing profiles are skipped rather than aborting the whole batch;
        adapters with a cheaper native bulk call may override this.
        """
        out: list[AggregatedProfile] = []
        for handle, platform in handles:
            try:
                out.append(self.fetch_profile(handle, platform, max_posts=max_posts))
            except ProfileNotFound:
                continue
        return out
