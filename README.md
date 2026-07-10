# Impact Desk — Influencer Impact Dashboard

Ranks influencers by the **median** of their per-post performance instead of the
average, so a single viral post can't make an inflated account look like a real
performer. Built to replace an influencer-marketing agency's 50-tab spreadsheet
with a dashboard a non-technical operator — and their clients — can actually read.

See [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md) for the full product brief.

## Repository layout

| Path | What it is |
|------|-----------|
| [`backend/`](./backend) | FastAPI + SQLAlchemy. The median-first metric engine, data model, the vendor-agnostic `AggregatorClient` (mock + CSV adapters), and the HTTP API. 43 tests. |
| [`frontend/`](./frontend) | React + TypeScript + Vite + Tailwind + Recharts. Ranked list, influencer detail with the median-vs-mean chart, and compare views. |
| [`docs/`](./docs) | Sales collateral: the go-live vendor brief and the demo walkthrough deck (HTML + PDF). |

## Why median, not mean

An account with nine dead posts and one viral hit *averages* 100,000 views but is
not a real influencer. Ranking by the median is robust to that, and the app flags
such accounts as **outlier-driven**. This logic is the heart of the product; see
[`backend/app/metrics.py`](./backend/app/metrics.py).

## Data source

All external data flows through one `AggregatorClient` interface, so the concrete
vendor is swappable without touching the rest of the app. Ships with a **mock**
adapter (realistic sample data — runs with no vendor or API key) and a
**CSV/manual** adapter. A paid aggregator becomes a third adapter; no vendor is
hardcoded. Vendor selection, cost, and terms-of-use compliance are open business
decisions — see `docs/`.

## Quickstart

```bash
# Backend  (http://127.0.0.1:8001, docs at /docs)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                       # build a demo DB
uvicorn app.main:app --port 8001

# Frontend (http://127.0.0.1:5173)
cd frontend
npm install
npm run dev
```

Read-only client view by default; operator actions (pull / import / recompute /
export) unlock with the operator token (dev default `dev-operator-token`).

> **Note:** the seeded influencers are synthetic sample data for demos, not real
> people. The app and analytics are real; only the underlying numbers are
> illustrative until a live data vendor is connected.
