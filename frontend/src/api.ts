// Typed client for the Influencer Impact Dashboard API.
// Base is proxied to the FastAPI backend (see vite.config.ts).

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface Metrics {
  post_count: number;
  median_views: number | null;
  median_likes: number | null;
  median_engagement: number | null;
  median_engagement_rate: number | null;
  mean_views: number | null;
  mean_likes: number | null;
  mean_engagement: number | null;
  mean_engagement_rate: number | null;
  views_mean_to_median_ratio: number | null;
  viral_post_count: number;
  is_outlier_driven: boolean;
  computed_at: string | null;
}

export interface RankedRow {
  id: number;
  handle: string;
  platform: string;
  display_name: string | null;
  follower_count: number | null;
  tier: string | null;
  rank: number;
  metrics: Metrics | null;
}

export interface PostRow {
  external_id: string | null;
  posted_at: string | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  engagement: number | null;
  engagement_rate: number | null;
}

export interface InfluencerDetail {
  id: number;
  handle: string;
  platform: string;
  display_name: string | null;
  follower_count: number | null;
  tier: string | null;
  metrics: Metrics | null;
  posts: PostRow[];
}

export interface CompareRow {
  id: number;
  handle: string;
  display_name: string | null;
  tier: string | null;
  median_views: number | null;
  median_engagement: number | null;
  median_engagement_rate: number | null;
  is_outlier_driven: boolean;
}

export type SortKey =
  | "median_views"
  | "median_engagement"
  | "median_engagement_rate"
  | "median_likes"
  | "follower_count"
  | "viral_post_count"
  | "post_count";

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface RankQuery {
  sort_by?: SortKey;
  order?: "asc" | "desc";
  tier?: string;
  platform?: string;
  min_posts?: number;
}

export const api = {
  async ranked(q: RankQuery = {}): Promise<RankedRow[]> {
    const params = new URLSearchParams();
    Object.entries(q).forEach(([k, v]) => v !== undefined && v !== "" && params.set(k, String(v)));
    return handle(await fetch(`${BASE}/influencers?${params}`));
  },

  async detail(id: number): Promise<InfluencerDetail> {
    return handle(await fetch(`${BASE}/influencers/${id}`));
  },

  async compare(ids: number[]): Promise<CompareRow[]> {
    return handle(await fetch(`${BASE}/influencers/compare?ids=${ids.join(",")}`));
  },

  // ---- operator actions (require token) ----
  async pull(token: string, handle_: string, platform: string): Promise<InfluencerDetail> {
    return handle(
      await fetch(`${BASE}/influencers/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders(token) },
        body: JSON.stringify({ handle: handle_, platform }),
      }),
    );
  },

  async importCsv(token: string, file: File): Promise<{ ingested: number }> {
    const form = new FormData();
    form.append("file", file);
    return handle(
      await fetch(`${BASE}/import/csv`, {
        method: "POST",
        headers: authHeaders(token),
        body: form,
      }),
    );
  },

  async recompute(
    token: string,
    engagement_formula?: { likes_weight: number; comments_weight: number; shares_weight: number },
  ): Promise<{ recomputed: number }> {
    return handle(
      await fetch(`${BASE}/recompute`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders(token) },
        body: JSON.stringify(engagement_formula ? { engagement_formula } : {}),
      }),
    );
  },

  // Export needs the operator token in a header, so fetch as a blob and
  // trigger a client-side download rather than linking directly.
  async exportCsv(token: string): Promise<Blob> {
    const res = await fetch(`${BASE}/export/ranked.csv`, { headers: authHeaders(token) });
    if (!res.ok) throw new Error(`export failed (${res.status})`);
    return res.blob();
  },
};

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
