import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type RankedRow, type SortKey } from "../api";
import { compact, pct } from "../lib/format";
import { useSession } from "../session";
import { Card, ErrorNote, OutlierBadge, Platform, Spinner, TierBadge, Button } from "./ui";

const COLUMNS: { key: SortKey; label: string; render: (r: RankedRow) => string }[] = [
  { key: "median_views", label: "Median views", render: (r) => compact(r.metrics?.median_views) },
  { key: "median_engagement_rate", label: "Median eng. rate", render: (r) => pct(r.metrics?.median_engagement_rate) },
  { key: "follower_count", label: "Followers", render: (r) => compact(r.follower_count) },
];

const TIERS = ["all", "macro", "micro", "nano"] as const;

export function RankedList() {
  const [rows, setRows] = useState<RankedRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("median_views");
  const [tier, setTier] = useState<(typeof TIERS)[number]>("all");
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();
  const { dataVersion } = useSession();

  useEffect(() => {
    setRows(null);
    setError(null);
    api
      .ranked({ sort_by: sortBy, order: "desc", tier: tier === "all" ? undefined : tier })
      .then(setRows)
      .catch((e) => setError(e.message));
  }, [sortBy, tier, dataVersion]);

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const outliers = useMemo(() => rows?.filter((r) => r.metrics?.is_outlier_driven).length ?? 0, [rows]);

  return (
    <div className="rise">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Who actually moves the needle
          </h1>
          <p className="mt-1 max-w-xl text-sm text-ink-soft">
            Ranked by <span className="font-medium text-ink">median</span> reach — robust to one-hit
            viral posts. {rows && (
              <>
                {rows.length} influencers, <span className="text-accent">{outliers}</span> flagged as
                outlier-driven.
              </>
            )}
          </p>
        </div>
        <div className="flex gap-1">
          {TIERS.map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                tier === t ? "bg-ink text-paper-raised" : "text-ink-soft hover:bg-paper-raised"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </header>

      {error && <ErrorNote message={error} />}
      {!rows && !error && <Spinner />}

      {rows && (
        <Card className="overflow-hidden">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-faint">
                <th className="w-10 py-3 pl-4"></th>
                <th className="w-10 py-3 font-medium">#</th>
                <th className="py-3 font-medium">Influencer</th>
                {COLUMNS.map((c) => (
                  <th key={c.key} className="py-3 pr-4 text-right font-medium">
                    <button
                      onClick={() => setSortBy(c.key)}
                      className={`inline-flex items-center gap-1 hover:text-ink ${
                        sortBy === c.key ? "text-ink" : ""
                      }`}
                    >
                      {c.label}
                      {sortBy === c.key && <span className="text-gold">▾</span>}
                    </button>
                  </th>
                ))}
                <th className="py-3 pr-4 text-right font-medium">Signal</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => navigate(`/influencers/${r.id}`)}
                  className="group cursor-pointer border-b border-line/60 last:border-0 transition-colors hover:bg-paper"
                >
                  <td className="py-3 pl-4" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.includes(r.id)}
                      onChange={() => toggle(r.id)}
                      className="accent-[color:var(--color-ink)]"
                      aria-label={`Select ${r.handle} to compare`}
                    />
                  </td>
                  <td className="py-3 font-display text-lg text-ink-faint nums">{r.rank}</td>
                  <td className="py-3">
                    <div className="font-medium text-ink group-hover:underline">
                      {r.display_name ?? r.handle}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-ink-faint">@{r.handle}</span>
                      <Platform name={r.platform} />
                      <TierBadge tier={r.tier} />
                    </div>
                  </td>
                  {COLUMNS.map((c) => (
                    <td key={c.key} className="py-3 pr-4 text-right nums tabular-nums text-ink">
                      {c.render(r)}
                    </td>
                  ))}
                  <td className="py-3 pr-4 text-right">
                    {r.metrics && <OutlierBadge real={!r.metrics.is_outlier_driven} />}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-16 text-center text-sm text-ink-faint">
                    No influencers yet. An operator can pull or import data to populate the board.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      {selected.length >= 2 && (
        <div className="fixed inset-x-0 bottom-6 flex justify-center">
          <Card className="flex items-center gap-3 px-4 py-2 shadow-lg rise">
            <span className="text-sm text-ink-soft">{selected.length} selected</span>
            <Button variant="ghost" onClick={() => setSelected([])}>
              Clear
            </Button>
            <Link to={`/compare?ids=${selected.join(",")}`}>
              <Button>Compare →</Button>
            </Link>
          </Card>
        </div>
      )}
    </div>
  );
}
