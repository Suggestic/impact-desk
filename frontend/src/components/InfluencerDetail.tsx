import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type InfluencerDetail as Detail } from "../api";
import { compact, full, pct, shortDate } from "../lib/format";
import { MedianMeanChart } from "./MedianMeanChart";
import { Card, ErrorNote, OutlierBadge, Platform, Spinner, TierBadge } from "./ui";

function Stat({
  label,
  median,
  mean,
  format = full,
}: {
  label: string;
  median: number | null;
  mean: number | null;
  format?: (n: number | null) => string;
}) {
  return (
    <div className="border-l border-line pl-4">
      <div className="text-xs uppercase tracking-wide text-ink-faint">{label}</div>
      <div className="mt-1 font-display text-2xl font-semibold text-ink nums">{format(median)}</div>
      <div className="text-xs text-ink-faint nums">
        mean {format(mean)} <span className="text-ink-faint/70">· comparison only</span>
      </div>
    </div>
  );
}

export function InfluencerDetail() {
  const { id } = useParams();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setD(null);
    api.detail(Number(id)).then(setD).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <ErrorNote message={error} />;
  if (!d) return <Spinner />;

  const m = d.metrics;
  const ratio = m?.views_mean_to_median_ratio;

  return (
    <div className="rise">
      <Link to="/" className="text-sm text-ink-soft hover:text-ink">
        ← Ranked list
      </Link>

      <header className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-semibold tracking-tight text-ink">
            {d.display_name ?? d.handle}
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <span className="text-sm text-ink-soft">@{d.handle}</span>
            <Platform name={d.platform} />
            <TierBadge tier={d.tier} />
            <span className="text-sm text-ink-faint nums">{compact(d.follower_count)} followers</span>
          </div>
        </div>
        {m && <OutlierBadge real={!m.is_outlier_driven} />}
      </header>

      {m && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Stat label="Median views" median={m.median_views} mean={m.mean_views} format={compact} />
            <Stat label="Median likes" median={m.median_likes} mean={m.mean_likes} format={compact} />
            <Stat
              label="Median eng. rate"
              median={m.median_engagement_rate}
              mean={m.mean_engagement_rate}
              format={pct}
            />
            <div className="border-l border-line pl-4">
              <div className="text-xs uppercase tracking-wide text-ink-faint">Consistency</div>
              <div className="mt-1 font-display text-2xl font-semibold text-ink nums">
                {ratio != null ? `${ratio.toFixed(1)}×` : "—"}
              </div>
              <div className="text-xs text-ink-faint">
                mean-to-median · {m.viral_post_count} viral {m.viral_post_count === 1 ? "post" : "posts"}
              </div>
            </div>
          </div>

          <Card className="mt-8 p-6">
            <div className="mb-1 flex items-baseline justify-between">
              <h2 className="font-display text-xl font-semibold text-ink">Reach distribution</h2>
              <span className="text-xs text-ink-faint">last {m.post_count} posts</span>
            </div>
            <p className="mb-4 max-w-2xl text-sm text-ink-soft">
              Each bar is one post. The <span className="text-gold">gold</span> line is the median;
              the <span className="text-accent">dashed vermilion</span> line is the mean. A mean
              floating far above the bars means a few outliers — not consistent reach — are inflating
              the average.
            </p>
            <MedianMeanChart posts={d.posts} median={m.median_views} mean={m.mean_views} />
          </Card>
        </>
      )}

      <Card className="mt-8 overflow-hidden">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-faint">
              <th className="py-3 pl-6 font-medium">Post</th>
              <th className="py-3 font-medium">Date</th>
              <th className="py-3 pr-4 text-right font-medium">Views</th>
              <th className="py-3 pr-4 text-right font-medium">Likes</th>
              <th className="py-3 pr-4 text-right font-medium">Engagement</th>
              <th className="py-3 pr-6 text-right font-medium">Eng. rate</th>
            </tr>
          </thead>
          <tbody>
            {d.posts.map((p, i) => (
              <tr key={p.external_id ?? i} className="border-b border-line/60 last:border-0">
                <td className="py-2.5 pl-6 text-ink-faint nums">{i + 1}</td>
                <td className="py-2.5 text-ink-soft">{shortDate(p.posted_at)}</td>
                <td className="py-2.5 pr-4 text-right text-ink nums">{full(p.views)}</td>
                <td className="py-2.5 pr-4 text-right text-ink-soft nums">{full(p.likes)}</td>
                <td className="py-2.5 pr-4 text-right text-ink-soft nums">{full(p.engagement)}</td>
                <td className="py-2.5 pr-6 text-right text-ink-soft nums">{pct(p.engagement_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
