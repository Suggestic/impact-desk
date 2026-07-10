"""Mock/fixture adapter — lets the whole app run end-to-end with no vendor.

Behaviour:
- A few *hand-authored* handles demonstrate the archetypes the operator cares
  about (a steady real influencer, an inflated one-viral-post account) across
  the emphasized platforms (TikTok, Instagram, YouTube).
- Any *other* handle gets plausible, **deterministic** data derived from the
  handle string, *shaped to the platform* — TikTok gets algorithmic reach far
  above follower count and prominent shares; Instagram gets tighter reach, a
  higher like-rate, and no share counts (the platform rarely exposes them);
  YouTube gets high accumulated views but a lower like-rate and comment-forward
  engagement. This makes the raw data differ realistically per platform, and
  mirrors what a real aggregator would return.

Data is generated at a fixed reference date so timestamps are stable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random
from typing import Optional

from .base import AggregatedPost, AggregatedProfile, AggregatorClient

_REFERENCE = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _seed(handle: str, platform: str) -> int:
    digest = hashlib.md5(f"{platform}:{handle}".encode()).hexdigest()
    return int(digest[:8], 16)


def _mk(i: int, views: int, likes: int, comments: int, shares: Optional[int]) -> AggregatedPost:
    return AggregatedPost(
        external_id=f"{i}",
        posted_at=_REFERENCE - timedelta(days=i * 2),
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
        raw={"source": "mock"},
    )


# --------------------------------------------------------------------------- #
# Per-platform behaviour. These ratios are what make the raw data look like it
# came from TikTok vs Instagram vs YouTube rather than one generic source.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Shape:
    reach: tuple[float, float]         # per-post views as a fraction of followers
    like_rate: tuple[float, float]     # likes / views
    comment_rate: tuple[float, float]  # comments / likes
    share_rate: Optional[tuple[float, float]]  # shares / likes; None => not exposed
    viral_chance: float
    viral_mult: tuple[int, int]


_SHAPES: dict[str, _Shape] = {
    # TikTok: reach can exceed follower count; shares are a first-class signal.
    "tiktok": _Shape((0.30, 1.40), (0.04, 0.09), (0.02, 0.05), (0.05, 0.12), 0.09, (12, 45)),
    # Instagram: tighter reach, higher like-rate, shares not exposed by the API.
    "instagram": _Shape((0.12, 0.45), (0.05, 0.12), (0.01, 0.04), None, 0.05, (6, 18)),
    # YouTube: high accumulated views, lower like-rate, comment-forward.
    "youtube": _Shape((0.40, 1.80), (0.02, 0.05), (0.03, 0.08), (0.004, 0.015), 0.06, (8, 28)),
}
_DEFAULT_SHAPE = _Shape((0.20, 0.80), (0.03, 0.08), (0.02, 0.05), (0.02, 0.06), 0.07, (10, 30))


def _authored(views_likes: list[tuple[int, int]], platform: str) -> list[AggregatedPost]:
    """Build hand-authored posts, deriving comments/shares per platform."""
    exposes_shares = platform.lower() != "instagram"
    out: list[AggregatedPost] = []
    for i, (v, k) in enumerate(views_likes):
        out.append(
            _mk(i, v, k, max(0, k // 10), (max(0, k // 20) if exposes_shares else None))
        )
    return out


# Hand-authored archetypes (newest-first), spanning the emphasized platforms ---
_KNOWN: dict[tuple[str, str], dict] = {
    ("steady_sam", "tiktok"): dict(
        display_name="Steady Sam",
        follower_count=850_000,
        posts=[(v, v // 20) for v in
               [180_000, 210_000, 195_000, 205_000, 190_000, 200_000,
                175_000, 215_000, 188_000, 202_000, 198_000, 192_000]],
    ),
    ("viral_vince", "tiktok"): dict(
        display_name="Viral Vince",
        follower_count=120_000,
        # 9 dead posts + 1 viral hit: mean says star, median says no.
        posts=[(0, 0)] * 9 + [(1_000_000, 40_000)],
    ),
    ("micro_mia", "instagram"): dict(
        display_name="Micro Mia",
        follower_count=32_000,
        posts=[(v, v // 15) for v in
               [9_000, 11_000, 10_000, 12_000, 9_500, 10_500, 11_500, 9_800]],
    ),
    ("lena_frame", "instagram"): dict(
        display_name="Lena Frame",
        follower_count=610_000,
        posts=[(v, v // 9) for v in
               [190_000, 205_000, 198_000, 212_000, 188_000, 201_000, 195_000, 208_000]],
    ),
    ("ghost_grid", "instagram"): dict(
        display_name="Ghost Grid",
        follower_count=480_000,
        # Big follower count, dead reach, one lucky reel: the classic fake.
        posts=[(0, 0), (900, 120), (0, 0), (1_100, 140), (0, 0),
               (0, 0), (780_000, 61_000), (0, 0)],
    ),
    ("marcus_long", "youtube"): dict(
        display_name="Marcus Long",
        follower_count=930_000,
        posts=[(v, int(v * 0.03)) for v in
               [140_000, 165_000, 150_000, 158_000, 172_000, 148_000, 161_000, 155_000]],
    ),
    ("flash_fry", "youtube"): dict(
        display_name="Flash Fry",
        follower_count=130_000,
        # One breakout video over an otherwise small channel.
        posts=[(v, int(v * 0.03)) for v in
               [8_000, 6_000, 7_000, 9_000, 5_000, 7_500, 3_100_000, 6_800]],
    ),
}


class MockAggregatorClient(AggregatorClient):
    name = "mock"

    def fetch_profile(
        self, handle: str, platform: str, *, max_posts: int = 20
    ) -> AggregatedProfile:
        key = (handle.lower(), platform.lower())
        if key in _KNOWN:
            fx = _KNOWN[key]
            posts = _authored(fx["posts"], platform)[:max_posts]
            return AggregatedProfile(
                handle=handle,
                platform=platform,
                display_name=fx["display_name"],
                follower_count=fx["follower_count"],
                posts=posts,
            )
        return self._generate(handle, platform, max_posts)

    def _generate(
        self, handle: str, platform: str, max_posts: int
    ) -> AggregatedProfile:
        rng = Random(_seed(handle, platform))
        shape = _SHAPES.get(platform.lower(), _DEFAULT_SHAPE)
        follower_count = rng.choice([5_000, 25_000, 80_000, 250_000, 900_000])

        posts: list[AggregatedPost] = []
        for i in range(max_posts):
            base = follower_count * rng.uniform(*shape.reach)
            if rng.random() < shape.viral_chance:
                base *= rng.randint(*shape.viral_mult)
            views = max(0, int(base))
            likes = int(views * rng.uniform(*shape.like_rate))
            comments = int(likes * rng.uniform(*shape.comment_rate))
            shares = None if shape.share_rate is None else int(likes * rng.uniform(*shape.share_rate))
            posts.append(_mk(i, views, likes, comments, shares))

        return AggregatedProfile(
            handle=handle,
            platform=platform,
            display_name=handle.replace("_", " ").title(),
            follower_count=follower_count,
            posts=posts,
        )
