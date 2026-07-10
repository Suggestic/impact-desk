# Influencer Impact Dashboard — Claude Code Handoff Brief

**Source:** "Suggestic Follow Up" call, July 2, 2026 (Carver Anderson, Rob Rusche, M. Dufresne)
**Prepared for:** Claude Code
**MVP scope:** Influencer-impact ranking dashboard. Media-spend analysis is a follow-on phase, out of scope for this build.

---

## 1. What we're building

A web app that replaces an influencer-marketing agency's sprawling manual spreadsheet (described on the call as "50 tabs and a million data points... a little overwhelming"). The app ingests per-influencer post metrics, computes **median** engagement (not average), and ranks influencers by real impact so the agency and its clients can see who actually moves the needle versus who looks big because of one viral post.

The end user is a non-technical agency operator. His clients need read access to the resulting dashboard to "select which influencer have the most impact." Keep the interface simple: he described wanting to "just type it in by person, and then it populates a dashboard instead of a spreadsheet."

## 2. The core problem this solves

The operator currently evaluates influencers by hand: he opens each public profile, scrolls the last ~20 posts, and records views, likes, and engagement. His pain is that **averages lie**. In his words: someone with 10 posts where 9 have zero views and 1 went viral with a million views "averages 100,000 per post, but really it was just one viral post." Averaging makes fake/inflated accounts "look like a major player when they weren't."

The fix he wants: rank by the **median** view/engagement per post, which is robust to viral outliers, so he can tell "who's real and who's not from the influencer perspective." This median-based scoring is the heart of the product. Get it right.

## 3. Data input (decided: aggregator API)

Direct scraping of platforms (TikTok, etc.) is off the table for terms-of-use reasons — this was a significant thread on the call ("they make it real hard to get actual information out of their system... no commercial paid option... doing it in a way that abides by the letter and spirit of the terms of use is challenging"). Today the operator pays an offshore assistant to collect the numbers by hand.

For this build, **assume a third-party influencer-data aggregator API** as the data source (the call noted "there are third party vendors that aggregate this stuff"). Design for this cleanly:

- Put all external data access behind a single `AggregatorClient` interface so the concrete vendor can be swapped without touching the rest of the app.
- Ship a **mock/fixture adapter** implementing that interface with realistic sample data, so the whole app is runnable end-to-end without a real vendor contract or API key.
- Also support **manual entry / CSV import** as a fallback adapter behind the same interface, since manual collection is the current reality and a likely bridge until a vendor is chosen.
- Do not hardcode any specific vendor. Treat vendor selection, cost, and T&C compliance as open items (see Section 8).

**Flag for the team:** vendor choice, pricing, and terms-of-use compliance are unresolved business decisions, not engineering ones. The code should make swapping vendors trivial; it should not assume a particular one exists.

## 4. Core metric logic (build this precisely)

For each influencer, pull the **last 20 posts** and per post capture: views, likes, engagement (engagement = likes + comments + shares, or whatever the aggregator exposes; make the formula explicit and configurable).

Compute and store per influencer:

- **Median views per post** (primary ranking metric)
- **Median likes per post**
- **Median engagement per post**
- **Median engagement rate** = median(engagement / views) per post, guarding against divide-by-zero
- Mean/average of each of the above, stored alongside **only for comparison**, never as the ranking metric
- **Consistency / outlier flags:** e.g. ratio of mean-to-median or count of posts more than N× the median, to surface accounts whose reach is carried by one or two viral posts. This directly serves the "who's real" question.

Rank influencers by median views (default), with the dashboard allowing re-sort by any stored metric. Never default to averages anywhere in ranking or headline numbers.

Edge cases to handle: influencers with fewer than 20 posts (use what's available, show the count), posts with zero views, and missing metrics from the aggregator.

## 5. Dashboard UI

Two roles:

- **Operator view (admin):** add/manage influencers, trigger a data pull (or enter/import data), see all metrics, adjust the engagement formula, export.
- **Client view (read-only):** browse and sort the ranked influencer list, drill into a single influencer's per-post breakdown and median vs mean comparison, filter by macro vs micro tiers (the call opened on "macro versus micro influencers" — support a configurable follower-count tier split).

Key screens:

1. **Ranked list** — sortable table of influencers with median views, median engagement rate, follower tier, and an outlier/consistency indicator.
2. **Influencer detail** — the last-20-posts table, a distribution chart showing median vs mean (make the outlier problem visually obvious), and the flags.
3. **Compare** — select several influencers side by side on median metrics to support selection decisions.

Keep it clean and non-technical. The whole point is that it's less overwhelming than the spreadsheet it replaces.

## 6. Suggested stack

Choose for fast delivery and easy client sharing; adjust if the team has standards.

- Frontend: React + a component library, charts via Recharts or similar.
- Backend: a thin API (Node/Express or Python/FastAPI) exposing influencer CRUD, metric computation, and the `AggregatorClient` abstraction.
- Storage: Postgres (or SQLite for the prototype). Store raw post rows plus computed metrics so recomputation is possible when the formula changes.
- Auth: simple role-based (operator vs read-only client) — enough to gate the two views, not enterprise SSO for the MVP.

## 7. Build order for Claude Code

1. Data model: influencers, posts, computed metrics; migrations and seed fixtures.
2. `AggregatorClient` interface + mock adapter with realistic sample data; CSV/manual adapter behind the same interface.
3. Metric engine: median-first computations and outlier flags, with unit tests covering the "9 zeros + 1 viral" case explicitly.
4. API endpoints.
5. Operator view, then client read-only view.
6. Charts and the median-vs-mean visualization.
7. Export (CSV/PDF of the ranked list).

## 8. Open items (business, not code)

- Which aggregator vendor, at what cost, and does its data licensing satisfy platform terms of use.
- Exact engagement formula the operator wants (confirm with him; make it configurable meanwhile).
- Macro/micro follower thresholds.
- Whether media-marketing-spend analysis (phase 2) reuses this data model — design the schema so it can.

## 9. Explicitly out of scope for this MVP

- Media marketing spend analysis (deferred to phase 2, though the data model should not preclude it).
- Any direct scraping of social platforms.
- The separate "meta ads campaign builder / innovation partner" opportunity mentioned late in the call — that is a different prospect ("Players" / the "from the future" call) and a separate project, not part of this build.
