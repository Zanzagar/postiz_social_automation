import { useQuery } from "@tanstack/react-query";
import {
  addDays,
  differenceInCalendarDays,
  differenceInMinutes,
  endOfDay,
  format,
  isSameDay,
  parseISO,
  startOfDay,
  subDays,
} from "date-fns";

import { api } from "@/lib/api";
import type {
  CalendarEntry,
  ContentRow,
  Festival,
  Pillar,
} from "@/lib/api";
import { pillarTarget } from "@/lib/pillars";

export type TimelineKind = "posted" | "review" | "upcoming";

export interface TimelineItem {
  id: number;
  kind: TimelineKind;
  /** e.g. "4:30 PM" — null when the row has no clock time */
  time: string | null;
  sortKey: number;
  title: string;
  platforms: string[];
  pillar: string | null;
  /** engagement-or-note caption line */
  caption: string;
  /** ISO timestamp when the post auto-releases (upcoming rows only) */
  autoPublishAt: string | null;
  held: boolean;
}

export interface PillarBalanceRow {
  name: string;
  color?: string | null;
  count: number;
  pct: number;
  target: number | null;
}

export interface FestivalItem {
  festival: Festival;
  daysUntil: number;
}

export interface DashboardStats {
  postedToday: number;
  awaitingReview: number;
  scheduledToday: number;
  dayStreak: number;
  lastPostedTime: string | null;
  nextReleaseTime: string | null;
  pendingPlatformCount: number;
}

/* ── pure helpers (exported for tests) ─────────────────────────────── */

function safeParse(value: string | null | undefined): Date | null {
  if (!value) return null;
  try {
    const d = parseISO(value);
    return Number.isNaN(d.getTime()) ? null : d;
  } catch {
    return null;
  }
}

export function platformIds(platforms: Record<string, boolean> | null | undefined): string[] {
  return Object.entries(platforms ?? {})
    .filter(([, on]) => on)
    .map(([id]) => id);
}

/**
 * Consecutive days (ending today, or yesterday if today has no post yet)
 * with at least one posted entry. 0 when the streak is broken.
 */
export function computeStreak(postedDates: ReadonlySet<string>, now: Date): number {
  let day = now;
  if (!postedDates.has(format(day, "yyyy-MM-dd"))) day = subDays(day, 1);
  let streak = 0;
  while (postedDates.has(format(day, "yyyy-MM-dd"))) {
    streak += 1;
    day = subDays(day, 1);
  }
  return streak;
}

/** "in 2h 14m" / "in 8m" / "any moment" for an auto-release timestamp. */
export function formatRemaining(iso: string, now: Date): string {
  const target = safeParse(iso);
  if (!target) return "";
  const mins = differenceInMinutes(target, now);
  if (mins <= 0) return "any moment";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`;
}

function toTimelineItem(
  id: number,
  status: string,
  title: string,
  platforms: string[],
  pillar: string | null,
  row: ContentRow | undefined,
): TimelineItem {
  const kind: TimelineKind =
    status === "posted" ? "posted" : status === "draft" ? "review" : "upcoming";
  const timeIso = kind === "posted" ? row?.posted_at : row?.auto_publish_at;
  const timeDate = safeParse(timeIso);
  const held = Boolean(row?.held_at);
  const autoPublishAt = kind === "upcoming" ? (row?.auto_publish_at ?? null) : null;
  const n = platforms.length;
  const caption =
    kind === "posted"
      ? `live on ${n} platform${n === 1 ? "" : "s"}`
      : kind === "review"
        ? "awaiting review"
        : held
          ? "held for review"
          : autoPublishAt
            ? "auto-release scheduled"
            : "queued";
  return {
    id,
    kind,
    time: timeDate ? format(timeDate, "h:mm a") : null,
    sortKey: timeDate ? timeDate.getTime() : Number.MAX_SAFE_INTEGER,
    title,
    platforms,
    pillar,
    caption,
    autoPublishAt,
    held,
  };
}

/** Today's calendar entries + pending drafts, merged and time-sorted. */
export function buildTimeline(
  entries: CalendarEntry[],
  drafts: ContentRow[],
  now: Date,
): TimelineItem[] {
  const byId = new Map(drafts.map((d) => [d.row_number, d]));
  const seen = new Set<number>();
  const items: TimelineItem[] = [];

  for (const e of entries) {
    const d = safeParse(e.date);
    if (!d || !isSameDay(d, now)) continue;
    items.push(
      toTimelineItem(
        e.row_number,
        e.status,
        e.raw_text,
        platformIds(e.platforms),
        e.content_pillar,
        byId.get(e.row_number),
      ),
    );
    seen.add(e.row_number);
  }

  for (const d of drafts) {
    if (d.status !== "draft" || seen.has(d.row_number)) continue;
    items.push(
      toTimelineItem(
        d.row_number,
        d.status,
        d.raw_text,
        platformIds(d.platforms),
        d.content_pillar,
        d,
      ),
    );
  }

  return items.sort((a, b) => a.sortKey - b.sortKey || a.title.localeCompare(b.title));
}

/** Last-30-days content mix per pillar, derived from calendar entries. */
export function computePillarBalance(
  entries: CalendarEntry[],
  pillars: Pillar[],
  now: Date,
): PillarBalanceRow[] {
  const windowStart = startOfDay(subDays(now, 29));
  const windowEnd = endOfDay(now);
  const counts = new Map<string, number>();
  for (const e of entries) {
    const d = safeParse(e.date);
    if (!d || d < windowStart || d > windowEnd) continue;
    if (!e.content_pillar) continue;
    counts.set(e.content_pillar, (counts.get(e.content_pillar) ?? 0) + 1);
  }
  const total = [...counts.values()].reduce((a, b) => a + b, 0);
  const byName = new Map(pillars.map((p) => [p.name, p]));
  const names = new Set<string>([
    ...pillars.filter((p) => p.is_active).map((p) => p.name),
    ...counts.keys(),
  ]);
  return [...names]
    .map((name) => {
      const pillar = byName.get(name);
      const count = counts.get(name) ?? 0;
      return {
        name,
        color: pillar?.color,
        count,
        pct: total > 0 ? Math.round((count / total) * 100) : 0,
        target: pillarTarget(pillar ?? name),
      };
    })
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

/** Posted-entries-per-day counts for the trailing `days` days (oldest first). */
export function computePulseSeries(
  entries: CalendarEntry[],
  now: Date,
  days = 14,
): number[] {
  const counts = new Map<string, number>();
  for (const e of entries) {
    if (e.status !== "posted") continue;
    const d = safeParse(e.date);
    if (!d) continue;
    const key = format(d, "yyyy-MM-dd");
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const series: number[] = [];
  for (let i = days - 1; i >= 0; i--) {
    series.push(counts.get(format(subDays(now, i), "yyyy-MM-dd")) ?? 0);
  }
  return series;
}

/* ── the hook ──────────────────────────────────────────────────────── */

export function useDashboardData() {
  const now = new Date();
  const todayIso = format(now, "yyyy-MM-dd");

  const drafts = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api.getDrafts(),
  });

  const calendar = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    staleTime: 5 * 60 * 1000,
  });

  const pillars = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
    staleTime: 5 * 60 * 1000,
  });

  const analytics = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => api.getAnalyticsOverview(),
  });

  const festivals = useQuery({
    queryKey: ["festivals", "dashboard", todayIso],
    queryFn: () =>
      api.getFestivals(todayIso, format(addDays(now, 120), "yyyy-MM-dd")),
    staleTime: 60 * 60 * 1000,
  });

  const knowledge = useQuery({
    queryKey: ["knowledge", "status"],
    queryFn: () => api.getKnowledgeStatus(),
    staleTime: 5 * 60 * 1000,
  });

  const draftRows = drafts.data ?? [];
  const entries = calendar.data?.entries ?? [];

  const pendingDrafts = draftRows.filter((d) => d.status === "draft");
  const timeline = buildTimeline(entries, draftRows, now);

  const postedToday = timeline.filter((t) => t.kind === "posted").length;
  const scheduledToday = timeline.filter((t) => t.kind === "upcoming").length;

  const postedDates = new Set(
    entries
      .filter((e) => e.status === "posted")
      .map((e) => safeParse(e.date))
      .filter((d): d is Date => d !== null)
      .map((d) => format(d, "yyyy-MM-dd")),
  );
  const dayStreak = computeStreak(postedDates, now);

  const postedTimes = draftRows
    .map((d) => safeParse(d.posted_at))
    .filter((d): d is Date => d !== null && isSameDay(d, now))
    .sort((a, b) => a.getTime() - b.getTime());
  const lastPostedTime = postedTimes.length
    ? format(postedTimes[postedTimes.length - 1], "h:mm a")
    : null;

  const upcomingReleases = draftRows
    .map((d) => safeParse(d.auto_publish_at))
    .filter((d): d is Date => d !== null && d.getTime() > now.getTime())
    .sort((a, b) => a.getTime() - b.getTime());
  const nextReleaseTime = upcomingReleases.length
    ? format(upcomingReleases[0], "h:mm a")
    : null;

  const pendingPlatformCount = new Set(
    pendingDrafts.flatMap((d) => platformIds(d.platforms)),
  ).size;

  const stats: DashboardStats = {
    postedToday,
    awaitingReview: pendingDrafts.length,
    scheduledToday,
    dayStreak,
    lastPostedTime,
    nextReleaseTime,
    pendingPlatformCount,
  };

  const festivalItems: FestivalItem[] = (festivals.data ?? [])
    .map((festival) => {
      const d = safeParse(festival.date);
      return d
        ? { festival, daysUntil: differenceInCalendarDays(d, now) }
        : null;
    })
    .filter((f): f is FestivalItem => f !== null && f.daysUntil >= 0)
    .sort((a, b) => a.daysUntil - b.daysUntil)
    .slice(0, 3);

  return {
    isLoading: drafts.isLoading || calendar.isLoading,
    isError: drafts.isError || calendar.isError,
    stats,
    timeline,
    pendingDrafts,
    pillars: pillars.data ?? [],
    pillarBalance: computePillarBalance(entries, pillars.data ?? [], now),
    festivals: festivalItems,
    overview: analytics.data,
    pulseSeries: computePulseSeries(entries, now),
    knowledge: knowledge.data,
    services: health.data?.services ?? [],
  };
}
