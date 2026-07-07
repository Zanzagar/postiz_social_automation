import { useMemo } from "react";
import {
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
} from "date-fns";

import { cn } from "@/lib/utils";

import { HAIRLINE, type CalendarEntryX } from "./calendar-utils";

const WEEK_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MAX_PILLS = 2;

interface MonthGridProps {
  /** Any date inside the month being shown */
  cursor: Date;
  entriesByDate: Record<string, CalendarEntryX[]>;
  colorFor: (name: string | null | undefined) => string;
  onEntryClick: (entry: CalendarEntryX) => void;
}

export function MonthGrid({
  cursor,
  entriesByDate,
  colorFor,
  onEntryClick,
}: MonthGridProps) {
  const today = new Date();

  const days = useMemo(() => {
    const monthStart = startOfMonth(cursor);
    const monthEnd = endOfMonth(cursor);
    return eachDayOfInterval({
      start: startOfWeek(monthStart, { weekStartsOn: 1 }),
      end: endOfWeek(monthEnd, { weekStartsOn: 1 }),
    });
  }, [cursor]);

  return (
    <div className="border-hair bg-card overflow-hidden rounded-2xl">
      <div className="border-hair-b grid grid-cols-7">
        {WEEK_LABELS.map((d) => (
          <div
            key={d}
            className="t-label ink-muted border-r px-3 py-2 text-center last:border-r-0"
            style={{ borderRightColor: HAIRLINE }}
          >
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const dateKey = format(day, "yyyy-MM-dd");
          const dayEntries = entriesByDate[dateKey] ?? [];
          const inMonth = isSameMonth(day, cursor);
          const isToday = isSameDay(day, today);
          const densityColor = dayEntries.length
            ? colorFor(dayEntries[0].content_pillar)
            : null;

          return (
            <div
              key={dateKey}
              className={cn(
                "aspect-[5/4] border-r border-b p-2 last:border-r-0",
                !inMonth && "bg-warm/50",
              )}
              style={{ borderRightColor: HAIRLINE, borderBottomColor: HAIRLINE }}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "t-body font-serif",
                    isToday
                      ? "font-semibold text-sage-800 dark:text-sage-100"
                      : inMonth
                        ? "ink"
                        : "ink-muted",
                  )}
                >
                  {format(day, "d")}
                </span>
                {densityColor && (
                  <div className="flex gap-0.5" aria-hidden="true">
                    {Array.from({ length: Math.min(dayEntries.length, 3) }).map(
                      (_, i) => (
                        <span
                          key={i}
                          className="h-1.5 w-1.5 rounded-sm"
                          style={{ background: densityColor }}
                        />
                      ),
                    )}
                  </div>
                )}
              </div>
              <div className="mt-1 space-y-1">
                {dayEntries
                  .filter((e) => e.raw_text)
                  .slice(0, MAX_PILLS)
                  .map((entry) => {
                    const color = colorFor(entry.content_pillar);
                    return (
                      <button
                        key={entry.row_number}
                        type="button"
                        onClick={() => onEntryClick(entry)}
                        className="fr t-micro block w-full rounded border-l-2 px-1.5 py-1 text-left"
                        style={{
                          background: `${color}18`,
                          borderLeftColor: color,
                        }}
                      >
                        <span className="ink block truncate font-medium">
                          {entry.raw_text}
                        </span>
                      </button>
                    );
                  })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
