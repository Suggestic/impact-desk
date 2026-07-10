"""CSV / manual-entry adapter — the bridge from today's spreadsheet reality.

The operator currently pays an assistant to collect numbers by hand into a
spreadsheet. This adapter accepts that same data behind the identical
`AggregatorClient` interface, so manual collection and a future paid vendor are
interchangeable to the rest of the app.

Expected CSV columns (header row required; extra columns are preserved in `raw`):

    platform, handle, display_name, follower_count,
    external_id, posted_at, views, likes, comments, shares

One row per post. Rows are grouped into profiles by (platform, handle).
`posted_at` is ISO-8601 (e.g. 2026-06-30 or 2026-06-30T12:00:00Z); blank
numeric cells become None (missing), not 0.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Iterable, Optional, Union

from .base import (
    AggregatedPost,
    AggregatedProfile,
    AggregatorClient,
    ProfileNotFound,
)

_CORE_COLUMNS = {
    "platform", "handle", "display_name", "follower_count",
    "external_id", "posted_at", "views", "likes", "comments", "shares",
}


def _int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    return int(float(value)) if value else None


def _dt(value: Optional[str]) -> Optional[datetime]:
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


class CSVAggregatorClient(AggregatorClient):
    """Loads profiles+posts from CSV text, a file path, or in-memory rows.

    Parsing happens once up front; `fetch_profile` then serves from memory,
    keeping it a drop-in peer of the mock and any live vendor.
    """

    name = "csv"

    def __init__(self, profiles: dict[tuple[str, str], AggregatedProfile]):
        self._profiles = profiles

    # ---- constructors -------------------------------------------------------
    @classmethod
    def from_path(cls, path: Union[str, Path]) -> "CSVAggregatorClient":
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_text(text)

    @classmethod
    def from_text(cls, text: str) -> "CSVAggregatorClient":
        return cls.from_rows(csv.DictReader(StringIO(text)))

    @classmethod
    def from_rows(cls, rows: Iterable[dict]) -> "CSVAggregatorClient":
        """Build from any iterable of dict rows (also serves 'manual entry')."""
        grouped: dict[tuple[str, str], dict] = {}
        for row in rows:
            platform = (row.get("platform") or "").strip()
            handle = (row.get("handle") or "").strip()
            if not platform or not handle:
                continue  # skip blank / malformed lines
            key = (handle.lower(), platform.lower())
            bucket = grouped.setdefault(
                key,
                {
                    "handle": handle,
                    "platform": platform,
                    "display_name": (row.get("display_name") or "").strip() or None,
                    "follower_count": _int(row.get("follower_count")),
                    "posts": [],
                },
            )
            extra = {k: v for k, v in row.items() if k not in _CORE_COLUMNS}
            bucket["posts"].append(
                AggregatedPost(
                    external_id=(row.get("external_id") or "").strip() or None,
                    posted_at=_dt(row.get("posted_at")),
                    views=_int(row.get("views")),
                    likes=_int(row.get("likes")),
                    comments=_int(row.get("comments")),
                    shares=_int(row.get("shares")),
                    raw=extra,
                )
            )

        profiles = {
            key: AggregatedProfile(
                handle=b["handle"],
                platform=b["platform"],
                display_name=b["display_name"],
                follower_count=b["follower_count"],
                # Newest-first so max_posts keeps the most recent; undated rows
                # sort last but preserve their input order.
                posts=sorted(
                    b["posts"],
                    key=lambda p: (p.posted_at is not None, p.posted_at or datetime.min.replace(tzinfo=None)),
                    reverse=True,
                ),
            )
            for key, b in grouped.items()
        }
        return cls(profiles)

    # ---- interface ----------------------------------------------------------
    def fetch_profile(
        self, handle: str, platform: str, *, max_posts: int = 20
    ) -> AggregatedProfile:
        key = (handle.lower(), platform.lower())
        profile = self._profiles.get(key)
        if profile is None:
            raise ProfileNotFound(f"{platform}:{handle} not present in CSV data")
        if len(profile.posts) <= max_posts:
            return profile
        return AggregatedProfile(
            handle=profile.handle,
            platform=profile.platform,
            display_name=profile.display_name,
            follower_count=profile.follower_count,
            posts=profile.posts[:max_posts],
        )

    def available(self) -> list[tuple[str, str]]:
        """(handle, platform) pairs this client can serve."""
        return [(p.handle, p.platform) for p in self._profiles.values()]
