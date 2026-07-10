import { useRef, useState } from "react";
import { api, downloadBlob } from "../api";
import { useSession } from "../session";
import { Button } from "./ui";

// Operator-only actions (§5): trigger a pull, import a CSV, recompute, export.
// Rendered in a slide-over; hidden entirely for read-only clients.
export function OperatorPanel({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const { token } = useSession();
  const [handle, setHandle] = useState("");
  const [platform, setPlatform] = useState("tiktok");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const run = async (fn: () => Promise<string>) => {
    if (!token) return;
    setBusy(true);
    setNote(null);
    try {
      setNote(await fn());
      onChanged();
    } catch (e) {
      setNote(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-ink/20" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm overflow-y-auto bg-paper-raised p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl font-semibold text-ink">Operator tools</h2>
          <Button variant="ghost" onClick={onClose}>
            ✕
          </Button>
        </div>

        <section className="mt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Pull one influencer
          </h3>
          <p className="mt-1 text-xs text-ink-soft">
            Fetches the last 20 posts via the configured aggregator and recomputes.
          </p>
          <div className="mt-3 space-y-2">
            <input
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="handle (e.g. viral_vince)"
              className="w-full rounded-md border border-line-strong bg-paper px-3 py-2 text-sm outline-none focus:border-ink"
            />
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full rounded-md border border-line-strong bg-paper px-3 py-2 text-sm outline-none focus:border-ink"
            >
              <option value="tiktok">TikTok</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
            </select>
            <Button
              disabled={busy || !handle.trim()}
              onClick={() =>
                run(async () => {
                  const d = await api.pull(token!, handle.trim(), platform);
                  return `Pulled @${d.handle}: median ${d.metrics?.median_views ?? "—"} views.`;
                })
              }
              className="w-full"
            >
              Trigger pull
            </Button>
          </div>
        </section>

        <hr className="my-6 border-line" />

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Import CSV</h3>
          <p className="mt-1 text-xs text-ink-soft">
            Manual / assistant-collected rows: platform, handle, followers, per-post views, likes…
          </p>
          <input ref={fileRef} type="file" accept=".csv" className="mt-3 block w-full text-xs" />
          <Button
            variant="outline"
            disabled={busy}
            className="mt-2 w-full"
            onClick={() =>
              run(async () => {
                const f = fileRef.current?.files?.[0];
                if (!f) throw new Error("choose a CSV file first");
                const r = await api.importCsv(token!, f);
                return `Imported ${r.ingested} influencer(s).`;
              })
            }
          >
            Upload &amp; ingest
          </Button>
        </section>

        <hr className="my-6 border-line" />

        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Maintenance</h3>
          <Button
            variant="outline"
            disabled={busy}
            className="w-full"
            onClick={() => run(async () => `Recomputed ${(await api.recompute(token!)).recomputed} influencers.`)}
          >
            Recompute all metrics
          </Button>
          <Button
            variant="outline"
            disabled={busy}
            className="w-full"
            onClick={() =>
              run(async () => {
                downloadBlob(await api.exportCsv(token!), "ranked_influencers.csv");
                return "Exported ranked_influencers.csv.";
              })
            }
          >
            Export ranked list (CSV)
          </Button>
        </section>

        {note && (
          <div className="mt-6 rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink-soft">
            {busy ? "Working…" : note}
          </div>
        )}
      </div>
    </div>
  );
}
