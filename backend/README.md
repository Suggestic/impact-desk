# Influencer Impact Dashboard — Backend

Data model, median-first metric engine, the vendor-agnostic aggregator seam,
and the FastAPI HTTP layer for the influencer-impact ranking MVP (see
`../PROJECT_BRIEF.md`). This is build steps **1–4** from the brief's §7. The
frontend (steps 5–6) is not built yet.

## Why median, not mean

The whole product exists because **averages lie**. An account with 9 zero-view
posts and 1 viral post averages 100k views but is not a real influencer. We
rank by the **median** (robust to viral outliers) and expose mean values only
for comparison. See the seed output below.

## Layout

| File | Role |
|------|------|
| `app/metrics.py` | **The engine.** Pure, ORM-free median-first computations + outlier flags. |
| `app/models.py` | ORM: `Influencer`, `Post` (raw signals), `InfluencerMetrics` (computed snapshot). |
| `app/aggregator/` | **The vendor seam.** `AggregatorClient` interface + `mock` and `csv` adapters + `get_client()` factory. |
| `app/ingest.py` | Lands an `AggregatedProfile` into the DB (idempotent upsert) and recomputes. |
| `app/main.py` | **FastAPI app.** Ranked list, detail, compare (read); create, pull, import, recompute, export (operator). |
| `app/schemas.py` | Pydantic request/response models (medians lead every payload). |
| `app/deps.py` | DB session + the operator/client role gate. |
| `app/service.py` | Bridges stored posts → engine → persisted metrics snapshot. |
| `app/config.py` | Tunable knobs: engagement formula, outlier thresholds, macro/micro tier split. |
| `app/db.py` | Engine/session; SQLite for prototype, Postgres/Supabase via `DATABASE_URL`. |
| `app/seed.py` | Realistic fixtures incl. the "9 zeros + 1 viral" account. |
| `tests/` | 31 tests: metric engine, aggregator adapters, and the full ingest path. |

## The aggregator seam (why no vendor is named)

Direct scraping is off the table and the paid vendor is an unresolved business
decision (§3/§8), so **all** external data flows through one interface,
`AggregatorClient`, and nothing downstream knows which source is wired in:

- **`mock`** (default) — realistic, deterministic sample data; the app runs
  end-to-end with **no vendor or API key**. Hand-authored archetypes
  (`steady_sam`, `viral_vince`, `micro_mia`) plus deterministic generation for
  any other handle.
- **`csv`** — the operator's current reality (assistant collecting numbers by
  hand). Accepts a CSV file, raw CSV text, or in-memory rows (manual entry).

A future paid vendor (Modash, CreatorDB, …) is just a **new adapter + one branch
in `get_client()`** — callers never change. Select via `AGGREGATOR` env var.

```python
from app.aggregator import get_client
from app.ingest import pull_and_ingest

client = get_client()                       # "mock" by default; "csv" with a path
pull_and_ingest(session, "viral_vince", "tiktok", client=client)
```

## Design decisions worth knowing

- **Raw posts are stored separately from computed metrics**, so changing the
  engagement formula recomputes from stored data with no aggregator round-trip.
- **Each metrics row snapshots the config used** (`engagement_formula`,
  `outlier_config`) → every stored ranking is reproducible and explainable.
- **Metrics are versioned, not overwritten** → keeps history and leaves room
  for the phase-2 media-spend model to join point-in-time metrics.
- **No aggregator vendor is referenced anywhere** — data access will live behind
  `AggregatorClient` (next step); mock/CSV adapters were chosen for the MVP.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest                 # 13 tests, incl. the "9 zeros + 1 viral" case
python -m app.seed     # builds influencer_rank.db and prints the ranking
```

Expected seed output:

```
Steady Sam     [macro] median_views=   197,500  mean_views=   196,000  viral_posts=0
Viral Vince    [macro] median_views=         0  mean_views=   100,000  viral_posts=1  <-- outlier-driven
Micro Mia      [micro] median_views=    10,250  mean_views=    10,412  viral_posts=0
```

`Viral Vince` is `macro` by follower count and has a 100k mean, yet a **median
of 0** — the engine flags him as outlier-driven. That contrast is the product.

## Run the API

```bash
uvicorn app.main:app --reload --port 8001    # docs at /docs
```

(The frontend's dev proxy targets `:8001` — see `../frontend/vite.config.ts`.
Any port is fine; keep the two in sync.)

Auth is minimal by design (§6): the **operator** sends
`Authorization: Bearer $OPERATOR_TOKEN` (default `dev-operator-token`) and may
write; everyone else is a read-only **client**. Swap for Supabase Auth/JWT later
without touching the endpoints.

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| GET | `/influencers` | client | Ranked list. `?sort_by=&order=&tier=&platform=&min_posts=`. Defaults to **median_views**; averages are rejected as sort keys. |
| GET | `/influencers/{id}` | client | Detail: last-N posts, median-vs-mean, flags. |
| GET | `/influencers/compare?ids=1,2,3` | client | Side-by-side on median metrics. |
| POST | `/influencers` | operator | Create an influencer. |
| POST | `/influencers/pull` | operator | Trigger an aggregator pull for one person. |
| POST | `/import/csv` | operator | Bulk import manual/assistant-collected CSV. |
| POST | `/recompute` | operator | Re-score all, optionally with a new engagement formula. |
| DELETE | `/influencers/{id}` | operator | Remove an influencer. |
| GET | `/export/ranked.csv` | operator | Export the ranked list (median-first columns). |

Example ranked output (via the mock aggregator):

```
#1 steady_sam   [macro] median_views=   196,500  mean=   195,833
#2 micro_mia    [micro] median_views=    10,250  mean=    10,412
#3 viral_vince  [macro] median_views=         0  mean=   100,000 <-- outlier-driven
```

## Configuration (env vars)

| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:///./influencer_rank.db` | Set to a Supabase Postgres URL in prod. |
| `POSTS_PER_INFLUENCER` | `20` | Most-recent posts scored per influencer. |
| `AGGREGATOR` | `mock` | Data source: `mock` or `csv`. |
| `AGGREGATOR_CSV_PATH` | — | CSV file path when `AGGREGATOR=csv`. |
| `OPERATOR_TOKEN` | `dev-operator-token` | Bearer token that grants operator (write) access. |

Engagement weights and macro/micro thresholds are in `app/config.py`.

## Next steps (per brief §7)

5. Operator view, then client read-only view (React + shadcn/ui).
6. Charts + the median-vs-mean visualization (Recharts).
7. Export (PDF of the ranked list; CSV export already exists).
