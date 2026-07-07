import { format, isSameDay } from "date-fns";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState, PlatformDots, STATUS_META } from "@/components/pasture";
import { cn } from "@/lib/utils";

import { AutoDot } from "./AutoDot";
import {
  HAIRLINE,
  entryPlatforms,
  entryTime,
  type CalendarEntryX,
} from "./calendar-utils";

interface WeekGridProps {
  /** 7 days, Monday first */
  weekDays: Date[];
  entriesByDate: Record<string, CalendarEntryX[]>;
  colorFor: (name: string | null | undefined) => string;
  onEntryClick: (entry: CalendarEntryX) => void;
  onAddSlot: (dateKey: string) => void;
  onPlant: () => void;
}

export function WeekGrid({
  weekDays,
  entriesByDate,
  colorFor,
  onEntryClick,
  onAddSlot,
  onPlant,
}: WeekGridProps) {
  const today = new Date();
  const weekIsEmpty = weekDays.every(
    (d) => (entriesByDate[format(d, "yyyy-MM-dd")] ?? []).length === 0,
  );

  return (
    <div className="border-hair bg-card overflow-hidden rounded-2xl">
      {/* Day header */}
      <div className="border-hair-b grid grid-cols-7">
        {weekDays.map((date, i) => {
          const isToday = isSameDay(date, today);
          return (
            <div
              key={i}
              className={cn(
                "border-r px-3 py-2.5 text-center last:border-r-0",
                isToday && "bg-sage-50 dark:bg-sage-800/40",
              )}
              style={{ borderRightColor: HAIRLINE }}
            >
              <div className="t-label ink-muted">{format(date, "EEE")}</div>
              <div
                className={cn(
                  "t-h2 mt-0.5 leading-none",
                  isToday ? "text-sage-800 dark:text-sage-100" : "ink",
                )}
              >
                {format(date, "d")}
              </div>
            </div>
          );
        })}
      </div>

      {weekIsEmpty ? (
        <EmptyState
          className="min-h-[420px]"
          title="A quiet week on the pasture…"
          body="Nothing is planted for these seven days yet."
          action={
            <Button variant="soft" size="sm" className="fr" onClick={onPlant}>
              <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
              Plant something
            </Button>
          }
        />
      ) : (
        <div className="grid min-h-[520px] grid-cols-7">
          {weekDays.map((date, i) => {
            const dateKey = format(date, "yyyy-MM-dd");
            const dayEntries = entriesByDate[dateKey] ?? [];
            return (
              <div
                key={i}
                className="space-y-1.5 border-r p-1.5 last:border-r-0"
                style={{ borderRightColor: HAIRLINE }}
              >
                {dayEntries.map((entry) => (
                  <EventBlock
                    key={entry.row_number}
                    entry={entry}
                    color={colorFor(entry.content_pillar)}
                    onClick={() => onEntryClick(entry)}
                  />
                ))}
                <button
                  type="button"
                  aria-label={`Add a post on ${format(date, "EEEE, MMMM d")}`}
                  onClick={() => onAddSlot(dateKey)}
                  className="fr t-caption ink-muted flex w-full items-center justify-center gap-1 rounded-lg border border-dashed p-1.5 transition-colors hover:bg-sage-50/50 dark:hover:bg-sage-800/30"
                  style={{ borderColor: HAIRLINE }}
                >
                  <Plus size={11} strokeWidth={1.75} aria-hidden="true" /> slot
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EventBlock({
  entry,
  color,
  onClick,
}: {
  entry: CalendarEntryX;
  color: string;
  onClick: () => void;
}) {
  const meta = STATUS_META[entry.status] ?? STATUS_META.draft;
  const platforms = entryPlatforms(entry);
  // Auto entries surface the quiet clock dot instead of a status corner dot.
  const showCornerDot =
    !entry.auto_publish_at &&
    entry.status !== "scheduled" &&
    entry.status !== "empty";

  return (
    <button
      type="button"
      onClick={onClick}
      className="fr t-caption relative w-full cursor-pointer rounded-lg border px-2 py-1.5 text-left leading-tight transition hover:shadow-sm"
      style={{
        background: `${color}12`,
        borderColor: `${color}40`,
        borderLeftWidth: 3,
        borderLeftColor: color,
      }}
    >
      <div className="mb-0.5 flex items-center gap-1">
        <span className="t-micro ink-muted font-mono">{entryTime(entry)}</span>
        <PlatformDots ids={platforms.slice(0, 3)} size={8} />
        {platforms.length > 3 && (
          <span className="t-micro ink-muted">+{platforms.length - 3}</span>
        )}
        <span className="flex-1" />
        {entry.auto_publish_at && <AutoDot />}
      </div>
      <div className="ink line-clamp-2 font-medium">
        {entry.raw_text || "— empty —"}
      </div>
      {showCornerDot && (
        <span
          className={cn("absolute top-1 right-1 h-1.5 w-1.5 rounded-full", meta.dot)}
          aria-hidden="true"
        />
      )}
    </button>
  );
}
