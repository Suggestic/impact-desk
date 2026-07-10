# Influencer Impact Dashboard — Frontend

React + TypeScript + Vite + Tailwind v4 + Recharts. This is build steps **5–6**
from `../PROJECT_BRIEF.md` §7: the operator and client views and the
median-vs-mean visualization. Talks to the FastAPI backend in `../backend`.

## Design

An **editorial data-desk** aesthetic — warm paper/ink palette, Fraunces (serif
display) + Geist (grotesque with tabular numerals), generous whitespace. One
vermilion accent is reserved exclusively for the **outlier-driven** ("not real")
signal, one moss green for **consistent** influencers, so "who's real" reads at a
glance. The goal, per the brief, is to feel *less overwhelming than the
spreadsheet it replaces*.

## Screens (§5)

| Route | Screen | Notes |
|-------|--------|-------|
| `/` | **Ranked list** | Sortable by median metrics, tier filter, per-row outlier signal, multi-select → compare. Default sort is median views. |
| `/influencers/:id` | **Detail** | Median-first stat strip (means labelled comparison-only), the **reach distribution chart** (each post a bar; gold median line, dashed vermilion mean line), and the last-N-posts table. |
| `/compare` | **Compare** | Selected influencers side by side on median metrics; highest median reach highlighted. |

## Roles (§6)

Read-only **client** by default. **Operator sign-in** (top bar) stores a bearer
token and unlocks the *Tools* slide-over: trigger a pull, import CSV, recompute,
export. Mirrors the backend's `require_operator` gate. Dev token:
`dev-operator-token`.

## Run

The backend must be running first (see `../backend/README.md`). Then:

```bash
npm install
npm run dev          # http://127.0.0.1:5173
```

Vite proxies `/api/*` to the backend (default `http://127.0.0.1:8001`, set in
`vite.config.ts`). Override the API base with `VITE_API_BASE` if needed.

```bash
npm run build        # tsc typecheck + production bundle to dist/
```
