"""FastAPI app: influencer CRUD, data pulls, ranking, and export.

Two audiences (§5):
- read endpoints serve the client (read-only) *and* operator views: ranked
  list, influencer detail, compare.
- write endpoints (create, pull, import, recompute, delete) require operator
  auth via `require_operator`.

Ranking defaults to **median views** and never to an average.
"""

from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .aggregator import CSVAggregatorClient, get_client
from .config import DEFAULT_TIER_CONFIG
from .db import init_db
from .deps import get_db, require_operator
from .ingest import ingest_profile, pull_and_ingest
from .metrics import EngagementFormula, OutlierConfig
from .models import Influencer
from .schemas import (
    CompareRow,
    InfluencerCreate,
    InfluencerDetail,
    MetricsOut,
    PostOut,
    PullRequest,
    RankedRow,
    RecomputeRequest,
)
from .service import formula_from_snapshot, latest_metrics

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Influencer Impact Dashboard API", version="0.1.0", lifespan=lifespan)

# Fields the ranked list may be sorted by. All are medians or structural — an
# average is intentionally NOT offered as a ranking key.
SORTABLE = {
    "median_views",
    "median_engagement",
    "median_engagement_rate",
    "median_likes",
    "follower_count",
    "viral_post_count",
    "post_count",
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# Read endpoints (client + operator)
# --------------------------------------------------------------------------- #
@app.get("/influencers", response_model=list[RankedRow])
def ranked_list(
    db: Session = Depends(get_db),
    sort_by: str = Query("median_views"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    tier: Optional[str] = Query(None, description="macro | micro | nano"),
    platform: Optional[str] = None,
    min_posts: int = Query(0, ge=0),
) -> list[RankedRow]:
    """Ranked, sortable influencer list — the primary screen."""
    if sort_by not in SORTABLE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"sort_by must be one of {sorted(SORTABLE)} (averages are not rankable).",
        )

    influencers = db.query(Influencer).all()
    rows = []
    for inf in influencers:
        if tier and inf.tier != tier:
            continue
        if platform and inf.platform != platform:
            continue
        m = latest_metrics(inf)
        if m is None or m.post_count < min_posts:
            continue
        rows.append((inf, m))

    # Sort, pushing missing values to the bottom regardless of order.
    def key(pair):
        inf, m = pair
        val = getattr(m, sort_by, None) if sort_by != "follower_count" else inf.follower_count
        return (val is not None, val if val is not None else 0)

    rows.sort(key=key, reverse=(order == "desc"))

    return [
        RankedRow(
            id=inf.id,
            handle=inf.handle,
            platform=inf.platform,
            display_name=inf.display_name,
            follower_count=inf.follower_count,
            tier=inf.tier,
            rank=i + 1,
            metrics=MetricsOut.model_validate(m),
        )
        for i, (inf, m) in enumerate(rows)
    ]


@app.get("/influencers/compare", response_model=list[CompareRow])
def compare(
    ids: str = Query(..., description="Comma-separated influencer ids"),
    db: Session = Depends(get_db),
) -> list[CompareRow]:
    """Side-by-side comparison of several influencers on median metrics (§5)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ids must be integers")

    out = []
    for inf_id in id_list:
        inf = db.get(Influencer, inf_id)
        if inf is None:
            continue
        m = latest_metrics(inf)
        out.append(
            CompareRow(
                id=inf.id,
                handle=inf.handle,
                display_name=inf.display_name,
                tier=inf.tier,
                median_views=m.median_views if m else None,
                median_engagement=m.median_engagement if m else None,
                median_engagement_rate=m.median_engagement_rate if m else None,
                is_outlier_driven=m.is_outlier_driven if m else False,
            )
        )
    return out


@app.get("/influencers/{influencer_id}", response_model=InfluencerDetail)
def influencer_detail(
    influencer_id: int, db: Session = Depends(get_db)
) -> InfluencerDetail:
    """Single influencer: last-N posts, median-vs-mean, and flags."""
    inf = db.get(Influencer, influencer_id)
    if inf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "influencer not found")

    m = latest_metrics(inf)
    formula = formula_from_snapshot(m.engagement_formula if m else None)

    posts = []
    for p in inf.posts:  # relationship is ordered newest-first
        engagement = formula.compute(p.likes, p.comments, p.shares)
        rate = (
            engagement / p.views
            if engagement is not None and p.views not in (None, 0)
            else None
        )
        posts.append(
            PostOut(
                external_id=p.external_id,
                posted_at=p.posted_at,
                views=p.views,
                likes=p.likes,
                comments=p.comments,
                shares=p.shares,
                engagement=engagement,
                engagement_rate=rate,
            )
        )

    return InfluencerDetail(
        id=inf.id,
        handle=inf.handle,
        platform=inf.platform,
        display_name=inf.display_name,
        follower_count=inf.follower_count,
        tier=inf.tier,
        metrics=MetricsOut.model_validate(m) if m else None,
        posts=posts,
    )


# --------------------------------------------------------------------------- #
# Write endpoints (operator only)
# --------------------------------------------------------------------------- #
@app.post("/influencers", response_model=InfluencerDetail, status_code=status.HTTP_201_CREATED)
def create_influencer(
    body: InfluencerCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_operator),
) -> InfluencerDetail:
    exists = (
        db.query(Influencer)
        .filter_by(platform=body.platform, handle=body.handle)
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "influencer already exists")
    inf = Influencer(
        handle=body.handle,
        platform=body.platform,
        display_name=body.display_name,
        follower_count=body.follower_count,
        tier=DEFAULT_TIER_CONFIG.classify(body.follower_count),
    )
    db.add(inf)
    db.commit()
    db.refresh(inf)
    return influencer_detail(inf.id, db)


@app.post("/influencers/pull", response_model=InfluencerDetail)
def pull_influencer(
    body: PullRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_operator),
) -> InfluencerDetail:
    """Trigger a data pull for one person via the configured aggregator."""
    inf = pull_and_ingest(
        db, body.handle, body.platform, client=get_client(), max_posts=body.max_posts
    )
    return influencer_detail(inf.id, db)


@app.post("/import/csv")
def import_csv(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    _: str = Depends(require_operator),
) -> dict:
    """Bulk import manual/assistant-collected data from a CSV file."""
    text = file.file.read().decode("utf-8")
    client = CSVAggregatorClient.from_text(text)
    ingested = 0
    for handle, platform in client.available():
        ingest_profile(db, client.fetch_profile(handle, platform))
        ingested += 1
    return {"ingested": ingested}


@app.post("/recompute")
def recompute(
    body: RecomputeRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_operator),
) -> dict:
    """Re-score everyone, optionally under a new engagement formula/thresholds."""
    from .service import recompute_all

    kwargs = {}
    if body.engagement_formula:
        kwargs["engagement_formula"] = EngagementFormula(**body.engagement_formula.model_dump())
    if body.outlier_config:
        kwargs["outlier_config"] = OutlierConfig(**body.outlier_config.model_dump())
    results = recompute_all(db, **kwargs)
    return {"recomputed": len(results)}


@app.delete("/influencers/{influencer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_influencer(
    influencer_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_operator),
) -> None:
    inf = db.get(Influencer, influencer_id)
    if inf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "influencer not found")
    db.delete(inf)
    db.commit()


@app.get("/export/ranked.csv")
def export_ranked(
    db: Session = Depends(get_db),
    _: str = Depends(require_operator),
) -> StreamingResponse:
    """Export the ranked list as CSV (median-first columns)."""
    rows = ranked_list(
        db=db, sort_by="median_views", order="desc",
        tier=None, platform=None, min_posts=0,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["rank", "handle", "platform", "tier", "follower_count",
         "median_views", "median_engagement_rate", "viral_post_count",
         "is_outlier_driven", "mean_views_for_comparison"]
    )
    for r in rows:
        m = r.metrics
        writer.writerow(
            [r.rank, r.handle, r.platform, r.tier, r.follower_count,
             m.median_views, m.median_engagement_rate, m.viral_post_count,
             m.is_outlier_driven, m.mean_views]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ranked_influencers.csv"},
    )
