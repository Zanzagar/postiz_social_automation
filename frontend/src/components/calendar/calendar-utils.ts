import { format, parseISO } from "date-fns";

import type { CalendarEntry, ContentRow, Pillar } from "@/lib/api";
import { pillarColor } from "@/lib/pillars";

/**
 * The calendar API payload does not (yet) include `auto_publish_at` in its
 * typed shape — read it optionally so the quiet "auto" clock dot lights up
 * as soon as the backend starts sending it.
 */
export type CalendarEntryX = CalendarEntry & {
  auto_publish_at?: string | null;
};

/** Hairline border color — matches the .border-hair token utility. */
export const HAIRLINE = "color-mix(in oklab, var(--ink) 12%, transparent)";

/** Map a CalendarEntry onto the ContentRow shape (for editor prefill). */
export function entryToContentRow(entry: CalendarEntryX): ContentRow {
  return {
    row_number: entry.row_number,
    date: entry.date,
    content_pillar: entry.content_pillar,
    raw_text: entry.raw_text,
    media_url: null,
    platforms: entry.platforms,
    status: entry.status,
    captions: entry.captions as Record<string, string | null>,
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: entry.source ?? "manual",
    auto_publish_at: entry.auto_publish_at ?? null,
    require_review: false,
    held_at: null,
    alt_text: null,
  };
}

export function dateKeyOf(entry: CalendarEntry): string {
  return format(parseISO(entry.date), "yyyy-MM-dd");
}

/** Group entries by yyyy-MM-dd, each day sorted by time. */
export function groupEntriesByDate(
  entries: CalendarEntryX[],
): Record<string, CalendarEntryX[]> {
  const map: Record<string, CalendarEntryX[]> = {};
  for (const e of entries) {
    const key = dateKeyOf(e);
    (map[key] ??= []).push(e);
  }
  for (const key of Object.keys(map)) {
    map[key].sort(
      (a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime(),
    );
  }
  return map;
}

/** Enabled platform ids for an entry, in a stable order. */
export function entryPlatforms(entry: CalendarEntry): string[] {
  return Object.entries(entry.platforms)
    .filter(([, on]) => on)
    .map(([id]) => id);
}

/** Time label like "4:30 PM" from the entry's datetime. */
export function entryTime(entry: CalendarEntry): string {
  try {
    return format(parseISO(entry.date), "h:mm a");
  } catch {
    return "";
  }
}

/**
 * Build a display-color lookup for pillar names. Pillars are dynamic —
 * colors come from GET /api/pillars, falling back to pillarColor()'s
 * stable hash for unknown names.
 */
export function makePillarColorLookup(
  pillars: Pillar[],
): (name: string | null | undefined) => string {
  const byName = new Map(pillars.map((p) => [p.name, p]));
  return (name) => {
    if (!name) return pillarColor("");
    return pillarColor(byName.get(name) ?? name);
  };
}
