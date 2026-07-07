import { differenceInMinutes } from "date-fns";

/** Serif row title — the first line of the raw text. */
export function draftTitle(rawText: string): string {
  const first = rawText.split("\n")[0]?.trim();
  return first || "Untitled draft";
}

/** "in 1h 24m" / "in 24m" / "now" until the auto-release moment. */
export function remainingLabel(target: Date, now: Date): string {
  const minutes = differenceInMinutes(target, now);
  if (minutes <= 0) return "now";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`;
}
