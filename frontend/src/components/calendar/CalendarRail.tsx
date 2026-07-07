import { useMemo } from "react";
import {
  addDays,
  differenceInCalendarDays,
  format,
  parseISO,
  startOfDay,
  startOfWeek,
} from "date-fns";

import type { Festival } from "@/lib/api";

import {
  HAIRLINE,
  type CalendarEntryX,
} from "./calendar-utils";

const HEATMAP_WEEKS = 12;
/** sage-500 — the heatmap ramp is brand-sage by design. */
const HEAT_RGB = "74,124,89";

interface CalendarRailProps {
  entriesByDate: Record<string, CalendarEntryX[]>;
  /** 7 days (Mon-first) of the week currently in view */
  weekDays: Date[];
  colorFor: (name: string | null | undefined) => string;
  festivals: Festival[];
}

export function CalendarRail({
  entriesByDate,
  weekDays,
  colorFor,
  festivals,
}: CalendarRailProps) {
  const today = startOfDay(new Date());

  const pillarCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const day of weekDays) {
      const key = format(day, "yyyy-MM-dd");
      for (const e of entriesByDate[key] ?? []) {
        if (!e.content_pillar) continue;
        counts.set(e.content_pillar, (counts.get(e.content_pillar) ?? 0) + 1);
      }
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [entriesByDate, weekDays]);

  const upcoming = useMemo(
    () =>
      festivals
        .map((f) => ({
          ...f,
          days: differenceInCalendarDays(parseISO(f.date), today),
        }))
        .filter((f) => f.days >= 0)
        .sort((a, b) => a.days - b.days)
        .slice(0, 4),
    [festivals, today],
  );

  return (
    <aside
      className="w-[320px] shrink-0 space-y-4 self-stretch border-l p-5"
      style={{
        borderLeftColor: HAIRLINE,
        background: "color-mix(in oklab, var(--surface-card) 60%, transparent)",
      }}
    >
      <div>
        <div className="t-label mb-2 text-sage-700 dark:text-sage-300">
          Posting density · 12 weeks
        </div>
        <Heatmap entriesByDate={entriesByDate} today={today} />
        <div className="t-micro ink-muted mt-2 flex items-center justify-between">
          <span>less</span>
          <div className="flex gap-0.5" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="h-2 w-3 rounded-sm"
                style={{ background: `rgba(${HEAT_RGB},${0.12 + i * 0.18})` }}
              />
            ))}
          </div>
          <span>more</span>
        </div>
      </div>

      <div className="border-t pt-4" style={{ borderTopColor: HAIRLINE }}>
        <div className="t-label mb-2 text-sage-700 dark:text-sage-300">
          Pillars this week
        </div>
        {pillarCounts.length === 0 ? (
          <p className="t-caption ink-muted">Nothing planted this week yet.</p>
        ) : (
          <div className="space-y-1.5">
            {pillarCounts.slice(0, 4).map(([name, count]) => (
              <div key={name} className="t-body-sm flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{ background: colorFor(name) }}
                  aria-hidden="true"
                />
                <span className="ink flex-1">{name}</span>
                <span className="ink-muted font-mono">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t pt-4" style={{ borderTopColor: HAIRLINE }}>
        <div className="t-label mb-2 text-sage-700 dark:text-sage-300">
          Upcoming festivals
        </div>
        {upcoming.length === 0 ? (
          <p className="t-caption ink-muted">No festivals on the horizon.</p>
        ) : (
          <div className="space-y-2">
            {upcoming.map((f) => {
              const d = parseISO(f.date);
              return (
                <div
                  key={`${f.name}-${f.date}`}
                  className="flex items-center gap-2.5 rounded-lg border border-cream-200 bg-cream-100/60 p-2 dark:border-cream-400/30 dark:bg-cream-400/10"
                >
                  <div className="flex h-8 w-8 flex-col items-center justify-center rounded bg-cream-300 leading-none dark:bg-cream-400/40">
                    <span className="t-micro font-semibold text-cream-ink uppercase">
                      {format(d, "MMM")}
                    </span>
                    <span className="t-caption font-serif text-cream-ink">
                      {format(d, "d")}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="t-body-sm ink truncate font-medium">
                      {f.name}
                    </div>
                    <div className="t-micro ink-muted">
                      {f.days === 0 ? "today" : `in ${f.days} day${f.days !== 1 ? "s" : ""}`}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}

/**
 * Posting-density heatmap: 12 columns (weeks) × 7 rows (Mon–Sun), ending
 * with the current week, computed from real calendar entries.
 */
function Heatmap({
  entriesByDate,
  today,
}: {
  entriesByDate: Record<string, CalendarEntryX[]>;
  today: Date;
}) {
  const currentWeekStart = startOfWeek(today, { weekStartsOn: 1 });

  return (
    <div
      className="grid gap-0.5"
      style={{ gridTemplateColumns: `repeat(${HEATMAP_WEEKS}, 1fr)` }}
      aria-hidden="true"
    >
      {Array.from({ length: HEATMAP_WEEKS }).map((_, w) => {
        const weekStart = addDays(currentWeekStart, (w - (HEATMAP_WEEKS - 1)) * 7);
        return (
          <div key={w} className="flex flex-col gap-0.5">
            {Array.from({ length: 7 }).map((_, d) => {
              const key = format(addDays(weekStart, d), "yyyy-MM-dd");
              const count = (entriesByDate[key] ?? []).length;
              const level = Math.min(count, 4);
              return (
                <div
                  key={d}
                  className="aspect-square rounded-sm"
                  style={{
                    background: `rgba(${HEAT_RGB},${0.1 + level * 0.18})`,
                  }}
                />
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
