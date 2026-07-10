import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PostRow } from "../api";
import { compact, full } from "../lib/format";

// The product's whole argument, made visual: each post's views as a bar, with
// the MEDIAN and MEAN drawn as horizontal reference lines. When one viral bar
// towers, the mean line floats far above the bulk while the median hugs where
// the posts actually live — "averages lie", at a glance.
export function MedianMeanChart({
  posts,
  median,
  mean,
}: {
  posts: PostRow[];
  median: number | null;
  mean: number | null;
}) {
  // Oldest-left, newest-right for a natural reading of the feed.
  const data = [...posts]
    .reverse()
    .map((p, i) => ({ i: i + 1, views: p.views ?? 0 }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 24, right: 16, bottom: 8, left: 8 }}>
          <XAxis
            dataKey="i"
            tick={{ fill: "var(--color-ink-faint)", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-line-strong)" }}
            label={{
              value: "posts (oldest → newest)",
              position: "insideBottom",
              offset: -2,
              fill: "var(--color-ink-faint)",
              fontSize: 11,
            }}
          />
          <YAxis
            tickFormatter={(v) => compact(v as number)}
            tick={{ fill: "var(--color-ink-faint)", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: "rgba(28,26,21,0.04)" }}
            contentStyle={{
              background: "var(--color-paper-raised)",
              border: "1px solid var(--color-line-strong)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v) => [full(v as number), "views"]}
            labelFormatter={(l) => `Post ${l}`}
          />
          <Bar dataKey="views" radius={[2, 2, 0, 0]} maxBarSize={44} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell
                key={i}
                // Bars above the mean line are the outliers doing the lying.
                fill={mean !== null && d.views > mean ? "var(--color-accent)" : "var(--color-line-strong)"}
              />
            ))}
          </Bar>
          {mean !== null && (
            <ReferenceLine
              y={mean}
              stroke="var(--color-accent)"
              strokeDasharray="5 4"
              strokeWidth={1.5}
              label={{
                value: `mean ${compact(mean)}`,
                position: "right",
                fill: "var(--color-accent)",
                fontSize: 11,
              }}
            />
          )}
          {median !== null && (
            <ReferenceLine
              y={median}
              stroke="var(--color-gold)"
              strokeWidth={2}
              label={{
                value: `median ${compact(median)}`,
                position: "right",
                fill: "var(--color-gold)",
                fontSize: 11,
              }}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
