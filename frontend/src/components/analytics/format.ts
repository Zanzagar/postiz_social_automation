import type { AnalyticsPostRow } from "@/lib/api";

/**
 * Shared formatting helpers + documented chart hexes for the Results page.
 * Hex values are chart colors from the design handoff — used only in SVG
 * attributes and inline styles, never in classNames.
 */

export const CHART_SAGE = "#4a7c59"; // sage-500 — current-period stroke
export const CHART_TERRA = "#b08968"; // terra-500 accent
export const CHART_CREAM = "#e6c46e"; // cream-500 accent
export const CHART_PRIOR = "#cbc3ad"; // prior-period dashed line
export const CHART_GRID = "#e9e2d0"; // dashed gridlines
export const CHART_INK = "#1e3224"; // sage-800 — peak tooltip fill

export type AccentTone = "sage" | "terra" | "cream";

export const ACCENT_COLORS: Record<AccentTone, string> = {
  sage: CHART_SAGE,
  terra: CHART_TERRA,
  cream: CHART_CREAM,
};

export interface RangeMeta {
  id: string;
  label: string;
  /** "this {noun}" — season sentence */
  noun: string;
  /** "your last {window}" — heatmap caption */
  window: string;
}

export const RANGES: RangeMeta[] = [
  { id: "7d", label: "7d", noun: "week", window: "7 days" },
  { id: "30d", label: "30d", noun: "month", window: "30 days" },
  { id: "90d", label: "90d", noun: "quarter", window: "90 days" },
  { id: "365d", label: "Year", noun: "year", window: "year" },
  // "all" = no lower time bound. Captions built from noun/window special-case
  // this id where "this all time"/"your last period" would read wrong.
  { id: "all", label: "All time", noun: "all time", window: "period" },
];

export function rangeMeta(range: string): RangeMeta {
  return RANGES.find((r) => r.id === range) ?? RANGES[1];
}

/** Parse date-only strings as local dates (avoids UTC-midnight day shifts). */
export function parseDate(value: string): Date {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return new Date(value);
}

/** "2026-03-08" → "Mar 8" (falls back to the raw string when unparseable). */
export function shortDate(value: string): string {
  const d = parseDate(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function trimmed(v: number): string {
  const s = v.toFixed(1);
  return s.endsWith(".0") ? s.slice(0, -2) : s;
}

/** 18200 → "18.2k", 1200000 → "1.2m", 340 → "340". */
export function compactNumber(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${trimmed(n / 1_000_000)}m`;
  if (abs >= 1_000) return `${trimmed(n / 1_000)}k`;
  return n.toLocaleString();
}

/** Engagement rate → "4.8%", or "—" when the rate is unknowable. */
export function formatRate(rate: number | null): string {
  if (rate === null) return "—";
  return `${trimmed(rate)}%`;
}

/** Signed percent delta, or null when unknowable (element is then omitted). */
export function formatDelta(delta: number | null): string | null {
  if (delta === null) return null;
  return `${delta >= 0 ? "+" : ""}${trimmed(delta)}%`;
}

/** Client-side CSV of the posts table — no backend export endpoint exists. */
export function buildResultsCsv(rows: AnalyticsPostRow[]): string {
  const esc = (v: string) => `"${v.replaceAll('"', '""')}"`;
  const header = [
    "Title",
    "Pillar",
    "Platforms",
    "Date",
    "Engagement",
    "Rate",
    "Trend",
    "Source",
  ];
  const lines = rows.map((r) =>
    [
      esc(r.title),
      esc(r.pillar ?? ""),
      esc(r.platforms.join("|")),
      esc(r.date),
      String(r.engagement),
      r.rate === null ? "" : String(r.rate),
      r.trend,
      r.source,
    ].join(","),
  );
  return [header.join(","), ...lines].join("\n");
}
