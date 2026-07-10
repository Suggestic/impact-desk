import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type CompareRow } from "../api";
import { compact, pct } from "../lib/format";
import { Card, ErrorNote, OutlierBadge, Spinner } from "./ui";

// Side-by-side on median metrics to support the selection decision (§5).
export function Compare() {
  const [params] = useSearchParams();
  const [rows, setRows] = useState<CompareRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ids = (params.get("ids") ?? "")
    .split(",")
    .map(Number)
    .filter((n) => !Number.isNaN(n));

  useEffect(() => {
    if (ids.length === 0) return;
    api.compare(ids).then(setRows).catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.get("ids")]);

  const best = rows ? Math.max(...rows.map((r) => r.median_views ?? 0)) : 0;

  return (
    <div className="rise">
      <Link to="/" className="text-sm text-ink-soft hover:text-ink">
        ← Ranked list
      </Link>
      <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-ink">
        Compare on median impact
      </h1>

      {error && <div className="mt-4"><ErrorNote message={error} /></div>}
      {!rows && !error && <Spinner />}

      {rows && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((r) => {
            const leads = (r.median_views ?? 0) === best && best > 0;
            return (
              <Card key={r.id} className={`p-5 ${leads ? "ring-1 ring-gold" : ""}`}>
                <div className="flex items-start justify-between">
                  <Link to={`/influencers/${r.id}`} className="font-medium text-ink hover:underline">
                    {r.display_name ?? r.handle}
                  </Link>
                  <OutlierBadge real={!r.is_outlier_driven} />
                </div>
                <div className="mt-4 space-y-3">
                  <Metric label="Median views" value={compact(r.median_views)} highlight={leads} />
                  <Metric label="Median engagement" value={compact(r.median_engagement)} />
                  <Metric label="Median eng. rate" value={pct(r.median_engagement_rate)} />
                </div>
                {leads && (
                  <div className="mt-4 text-xs font-medium uppercase tracking-wide text-gold">
                    Highest median reach
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-baseline justify-between border-b border-line/60 pb-2">
      <span className="text-xs uppercase tracking-wide text-ink-faint">{label}</span>
      <span
        className={`font-display text-xl nums ${highlight ? "text-gold" : "text-ink"} font-semibold`}
      >
        {value}
      </span>
    </div>
  );
}
