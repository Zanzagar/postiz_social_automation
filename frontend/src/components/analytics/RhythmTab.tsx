import { Gift, Sprout } from "lucide-react";

import { cn } from "@/lib/utils";
import { Chip, EmptyState } from "@/components/pasture";
import type { FestivalLift, RhythmWeek, SeasonSummary } from "@/lib/api";
import { TabError, TabLoading } from "./TabFallbacks";
import { formatDelta, rangeMeta, shortDate } from "./format";

interface RhythmTabProps {
  weeks: RhythmWeek[];
  festivals: FestivalLift[];
  season: SeasonSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  range: string;
}

function CadenceCard({ weeks }: { weeks: RhythmWeek[] }) {
  const hasTargets = weeks.some((w) => w.target !== null);
  const scale = Math.max(...weeks.map((w) => w.posted), ...weeks.map((w) => w.target ?? 0), 1);
  return (
    <div className="bg-card border-hair shadow-card rounded-xl p-5">
      <div className="t-label text-sage-600 dark:text-sage-300">Cadence</div>
      <div className="t-h2 mt-0.5 mb-4 text-sage-800 dark:text-sage-100">
        Your posting rhythm, week-by-week
      </div>
      {weeks.length === 0 ? (
        <EmptyState
          icon={Sprout}
          title="No rhythm to read yet"
          body="Week-by-week pacing will appear once posts start flowing in this window."
        />
      ) : (
        <>
          <div className="space-y-2">
            {weeks.map((w) => (
              <div key={w.label} className="flex items-center gap-3">
                <span className="t-caption ink-muted w-20 shrink-0">{w.label}</span>
                <div className="relative h-5 flex-1 overflow-hidden rounded-md bg-sage-50 dark:bg-sage-800">
                  <div
                    className="absolute top-0 left-0 h-full bg-sage-500"
                    style={{ width: `${(w.posted / scale) * 100}%` }}
                  />
                  {w.target !== null && (
                    <div
                      className="absolute top-0 h-full border-r-2 border-dashed border-terra-400"
                      style={{ left: `${(w.target / scale) * 100}%` }}
                    />
                  )}
                </div>
                <span className="t-caption ink w-12 shrink-0 text-right font-mono">
                  {w.target !== null ? `${w.posted}/${w.target}` : w.posted}
                </span>
              </div>
            ))}
          </div>
          <div className="t-caption ink-muted mt-3 flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm bg-sage-500" aria-hidden="true" />
              Posted
            </span>
            {hasTargets && (
              <span className="flex items-center gap-1">
                <span
                  className="h-3 w-0 border-r-2 border-dashed border-terra-400"
                  aria-hidden="true"
                />
                Weekly target
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function FestivalsCard({ festivals }: { festivals: FestivalLift[] }) {
  return (
    <div className="bg-card border-hair shadow-card rounded-xl p-5">
      <div className="t-label text-sage-600 dark:text-sage-300">Festival days</div>
      <div className="t-h2 mt-0.5 mb-4 text-sage-800 dark:text-sage-100">
        Posts that rode the calendar
      </div>
      {festivals.length === 0 ? (
        <EmptyState
          icon={Gift}
          title="No festivals in this window"
          body="When the calendar brings a festival, its posts and their lift will gather here."
        />
      ) : (
        <div className="space-y-2.5">
          {festivals.map((f) => (
            <div
              key={`${f.date}-${f.name}`}
              className={cn(
                "flex items-center gap-3 rounded-lg border p-3",
                f.pending
                  ? "border-cream-300 bg-cream-50 dark:border-cream-400/40 dark:bg-cream-400/10"
                  : "border-sage-100 bg-sage-50/60 dark:border-sage-700 dark:bg-sage-800/60",
              )}
            >
              <Gift
                size={14}
                strokeWidth={1.75}
                className={
                  f.pending ? "text-cream-ink" : "text-sage-700 dark:text-sage-300"
                }
                aria-hidden="true"
              />
              <span className="t-body-sm ink w-16 shrink-0">{shortDate(f.date)}</span>
              <span className="t-ui ink min-w-0 flex-1 truncate font-medium">
                {f.name}
              </span>
              <span className="t-caption ink-muted shrink-0">{f.posts} posts</span>
              {f.pending ? (
                <Chip tone="cream">upcoming</Chip>
              ) : (
                f.lift_pct !== null && (
                  <span className="t-caption w-16 shrink-0 text-right font-medium text-sage-700 dark:text-sage-300">
                    {formatDelta(f.lift_pct)}
                  </span>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SeasonCard({ season, range }: { season: SeasonSummary; range: string }) {
  const meta = rangeMeta(range);
  const onTarget = season.consistency.on_target_weeks;
  return (
    <aside className="relative overflow-hidden rounded-xl bg-sage-800 p-5 text-cream-100">
      <div className="absolute -right-8 -bottom-8 opacity-10" aria-hidden="true">
        <Sprout size={160} strokeWidth={1} />
      </div>
      <div className="t-label text-cream-200/80">The season at a glance</div>
      <p className="t-title mt-2 leading-snug">
        You've published {season.total_posts} {season.total_posts === 1 ? "post" : "posts"}{" "}
        this {meta.noun}.
      </p>
      <div className="t-body-sm mt-4 space-y-1.5 border-t border-sage-600/40 pt-4 text-cream-200/80">
        {onTarget !== null && (
          <div className="flex justify-between gap-2">
            <span>Consistency</span>
            <span className="text-cream-100">
              {onTarget} of {season.consistency.total_weeks} weeks on target
            </span>
          </div>
        )}
        <div className="flex justify-between gap-2">
          <span>Best weekday</span>
          <span className="text-cream-100">
            {season.best_slot
              ? `${season.best_slot.day} ${season.best_slot.hour_bucket}`
              : "—"}
          </span>
        </div>
        <div className="flex justify-between gap-2">
          <span>Avg lead time</span>
          <span className="text-cream-100">
            {season.avg_lead_days !== null ? `${season.avg_lead_days} days` : "—"}
          </span>
        </div>
      </div>
    </aside>
  );
}

/** Rhythm — weekly cadence, festival lift, and the season summary. */
export function RhythmTab({
  weeks,
  festivals,
  season,
  isLoading,
  isError,
  range,
}: RhythmTabProps) {
  if (isLoading) return <TabLoading />;
  if (isError || !season) return <TabError />;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 space-y-4">
        <CadenceCard weeks={weeks} />
        <FestivalsCard festivals={festivals} />
      </div>
      <SeasonCard season={season} range={range} />
    </div>
  );
}
