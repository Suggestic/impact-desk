import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-lg border border-line bg-paper-raised shadow-[0_1px_0_rgba(28,26,21,0.03),0_8px_24px_-18px_rgba(28,26,21,0.25)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "solid",
  type = "button",
  disabled,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "solid" | "outline" | "ghost";
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none";
  const styles = {
    solid: "bg-ink text-paper-raised hover:bg-ink-soft",
    outline: "border border-line-strong text-ink hover:bg-paper",
    ghost: "text-ink-soft hover:text-ink hover:bg-paper",
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${styles} ${className}`}>
      {children}
    </button>
  );
}

export function OutlierBadge({ real }: { real: boolean }) {
  // The single most important visual signal in the product: is this reach real?
  return real ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--color-real)]/30 bg-real-soft px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-real">
      <Dot className="fill-real" /> Consistent
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--color-accent)]/30 bg-accent-soft px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-accent">
      <Dot className="fill-accent" /> Outlier-driven
    </span>
  );
}

export function TierBadge({ tier }: { tier: string | null }) {
  if (!tier || tier === "unknown")
    return <span className="text-xs text-ink-faint">—</span>;
  return (
    <span className="rounded border border-line-strong px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-soft">
      {tier}
    </span>
  );
}

export function Platform({ name }: { name: string }) {
  return <span className="text-xs uppercase tracking-wide text-ink-faint">{name}</span>;
}

function Dot({ className }: { className: string }) {
  return (
    <svg width="6" height="6" viewBox="0 0 6 6" className={className} aria-hidden>
      <circle cx="3" cy="3" r="3" />
    </svg>
  );
}

export function Spinner() {
  return (
    <div className="flex items-center gap-2 py-16 text-sm text-ink-faint">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-line-strong border-t-ink" />
      Loading…
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-[color:var(--color-accent)]/30 bg-accent-soft px-4 py-3 text-sm text-accent">
      {message}
    </div>
  );
}
