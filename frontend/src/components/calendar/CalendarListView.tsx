import { format, isSameDay, isWeekend } from "date-fns";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PillarChip, PlatformDots, StatusPill } from "@/components/pasture";
import { cn } from "@/lib/utils";

import { AutoDot } from "./AutoDot";
import {
  entryPlatforms,
  entryTime,
  type CalendarEntryX,
} from "./calendar-utils";

interface CalendarListViewProps {
  /** 7 days, Monday first */
  weekDays: Date[];
  entriesByDate: Record<string, CalendarEntryX[]>;
  colorFor: (name: string | null | undefined) => string;
  onEntryClick: (entry: CalendarEntryX) => void;
  onAddSlot: (dateKey: string) => void;
}

export function CalendarListView({
  weekDays,
  entriesByDate,
  colorFor,
  onEntryClick,
  onAddSlot,
}: CalendarListViewProps) {
  const today = new Date();

  return (
    <div className="border-hair bg-card max-w-4xl overflow-hidden rounded-2xl">
      {weekDays.map((date, i) => {
        const dateKey = format(date, "yyyy-MM-dd");
        const items = entriesByDate[dateKey] ?? [];
        const isToday = isSameDay(date, today);
        const liveCount = items.filter((e) => e.status === "posted").length;

        return (
          <div key={i} className="border-hair-b last:border-b-0">
            {/* Day header row */}
            <div
              className={cn(
                "flex items-center gap-4 px-6 py-3",
                isToday ? "bg-sage-50 dark:bg-sage-800/40" : "bg-warm/50",
              )}
            >
              <div className="w-14 text-center">
                <div
                  className={cn(
                    "t-h1 leading-none",
                    isToday ? "text-sage-800 dark:text-sage-100" : "ink",
                  )}
                >
                  {format(date, "d")}
                </div>
                <div className="t-micro ink-muted mt-0.5 tracking-wider uppercase">
                  {format(date, "EEE")} · {format(date, "MMM")}
                </div>
              </div>
              <div className="flex-1">
                <div className="t-ui ink font-medium">
                  {isToday ? "Today" : isWeekend(date) ? "Weekend" : "This week"}
                </div>
                <div className="t-caption ink-muted">
                  {items.length} post{items.length !== 1 ? "s" : ""}
                  {isToday && liveCount > 0
                    ? ` · ${liveCount} already live`
                    : ""}
                </div>
              </div>
              <div className="flex items-center gap-1" aria-hidden="true">
                {items.slice(0, 4).map((entry, j) => (
                  <span
                    key={j}
                    className="h-2 w-6 rounded-sm"
                    style={{ background: colorFor(entry.content_pillar) }}
                  />
                ))}
              </div>
              <Button
                variant="ghost"
                size="iconSm"
                className="fr"
                aria-label={`Add a post on ${format(date, "EEEE, MMMM d")}`}
                onClick={() => onAddSlot(dateKey)}
              >
                <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
              </Button>
            </div>

            {/* Item rows */}
            {items.length > 0 ? (
              <div>
                {items.map((entry) => {
                  const color = colorFor(entry.content_pillar);
                  const platforms = entryPlatforms(entry);
                  return (
                    <button
                      key={entry.row_number}
                      type="button"
                      onClick={() => onEntryClick(entry)}
                      className="fr border-hair-b flex w-full cursor-pointer items-center gap-4 px-6 py-3 text-left last:border-b-0 hover:bg-sage-50/30 dark:hover:bg-sage-800/20"
                    >
                      <div className="w-14 text-right">
                        <div className="t-body-sm ink font-mono">
                          {entryTime(entry)}
                        </div>
                      </div>
                      <div
                        className="h-8 w-1 shrink-0 rounded-sm"
                        style={{ background: color }}
                        aria-hidden="true"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="t-body ink truncate font-medium">
                          {entry.raw_text || "— empty slot —"}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2">
                          {entry.content_pillar && (
                            <PillarChip
                              pillar={{
                                name: entry.content_pillar,
                                color,
                              }}
                              size="xs"
                            />
                          )}
                          <span className="t-caption ink-muted">·</span>
                          <PlatformDots ids={platforms} size={10} />
                          <span className="t-caption ink-muted">
                            {platforms.length} platform
                            {platforms.length !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                      {entry.auto_publish_at && <AutoDot />}
                      <StatusPill status={entry.status} size="xs" />
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="t-caption ink-muted px-6 py-4 text-center">
                Nothing scheduled —{" "}
                <button
                  type="button"
                  onClick={() => onAddSlot(dateKey)}
                  className="fr rounded-sm text-sage-600 underline dark:text-sage-300"
                >
                  add a post
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
