"""Seed the database with a realistic, multi-platform roster, then compute metrics.

The demo spans the emphasized platforms — TikTok, Instagram, YouTube — and the
raw per-post data is shaped to each one, so the board looks like it came from
real, differentiated sources rather than a single generic feed:

- TikTok:    algorithmic reach (views can dwarf follower count), prominent shares.
- Instagram: tighter reach, higher like-rate, NO share counts (the platform's
             API doesn't reliably expose them → stored as missing, not zero).
- YouTube:   high accumulated views, lower like-rate, comment-forward engagement.

Each platform includes the operator's core contrast: a genuinely consistent
influencer vs. an inflated account carried by one viral post.

Run with:  python -m app.seed
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import SessionLocal, init_db
from .models import Influencer, Post
from .service import recompute_all

_BASE = datetime(2026, 6, 1, tzinfo=timezone.utc)

# Deterministic per-platform engagement ratios (share=None => not exposed).
_RATIOS: dict[str, dict[str, Optional[float]]] = {
    "tiktok": {"like": 0.060, "comment": 0.004, "share": 0.015},
    "instagram": {"like": 0.090, "comment": 0.006, "share": None},
    "youtube": {"like": 0.030, "comment": 0.005, "share": 0.002},
}


def make_posts(platform: str, views_list: list[int]) -> list[Post]:
    """Derive likes/comments/shares from views using the platform's signature."""
    r = _RATIOS[platform]
    posts: list[Post] = []
    for i, v in enumerate(views_list):
        share_ratio = r["share"]
        posts.append(
            Post(
                external_id=f"p{i}",
                posted_at=_BASE - timedelta(days=i * 3),
                views=v,
                likes=int(v * r["like"]),
                comments=int(v * r["comment"]),
                shares=None if share_ratio is None else int(v * share_ratio),
            )
        )
    return posts


# (platform, handle, display, followers, views newest-first) --------------------
FIXTURES = [
    # ---- TikTok ----
    ("tiktok", "nova_reels", "Nova Reels", 1_200_000,
     [520_000, 610_000, 480_000, 560_000, 590_000, 505_000, 540_000, 575_000, 495_000, 560_000]),
    ("tiktok", "spike_steele", "Spike Steele", 280_000,
     [15_000, 12_000, 9_000, 14_000, 11_000, 13_000, 10_000, 12_000, 2_400_000, 14_000]),

    # ---- Instagram (no share counts) ----
    ("instagram", "lena_frame", "Lena Frame", 640_000,
     [190_000, 210_000, 205_000, 198_000, 215_000, 188_000, 202_000, 196_000, 209_000, 193_000]),
    ("instagram", "ghost_grid", "Ghost Grid", 500_000,
     [0, 0, 1_200, 0, 0, 900, 0, 0, 0, 780_000]),
    ("instagram", "micro_mia", "Micro Mia", 32_000,
     [11_000, 12_000, 10_000, 13_000, 9_500, 12_500, 11_800, 10_400]),

    # ---- YouTube ----
    ("youtube", "marcus_long", "Marcus Long", 900_000,
     [140_000, 165_000, 150_000, 158_000, 172_000, 148_000, 161_000, 155_000]),
    ("youtube", "flash_fry", "Flash Fry", 130_000,
     [8_000, 6_000, 7_000, 9_000, 5_000, 7_500, 3_100_000, 6_800]),
]


def seed() -> None:
    init_db()
    session = SessionLocal()
    try:
        for platform, handle, display, followers, views in FIXTURES:
            existing = (
                session.query(Influencer)
                .filter_by(platform=platform, handle=handle)
                .first()
            )
            if existing:
                continue
            session.add(
                Influencer(
                    handle=handle,
                    platform=platform,
                    display_name=display,
                    follower_count=followers,
                    posts=make_posts(platform, views),
                )
            )
        session.commit()

        results = recompute_all(session)
        print(f"Seeded {len(FIXTURES)} influencers across 3 platforms, "
              f"computed {len(results)} metric rows.\n")

        for inf in session.query(Influencer).order_by(Influencer.platform).all():
            m = inf.metrics[0]  # newest
            flag = "  <-- outlier-driven" if m.is_outlier_driven else ""
            print(
                f"{inf.platform:10s} {inf.display_name:14s} [{inf.tier:5s}] "
                f"median_views={m.median_views:>11,.0f}  "
                f"mean_views={m.mean_views:>11,.0f}{flag}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    seed()
