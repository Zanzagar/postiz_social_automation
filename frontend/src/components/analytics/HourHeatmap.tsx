import { cn } from "@/lib/utils";
import type { AnalyticsHeatmap } from "@/lib/api";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const LEGEND_STEPS = [0.15, 0.3, 0.5, 0.7, 0.9];

/** rgba(sage-500) at the given alpha — heatmap cells per the design. */
function sage(alpha: number): string {
  return `rgba(74,124,89,${alpha})`;
}

interface HourHeatmapProps {
  heatmap: AnalyticsHeatmap;
}

/**
 * "Best time to post" — 7 day rows × hour-bucket columns; cell intensity is
 * normalized to the grid max; the peak cell gets a terra ring and a star.
 */
export function HourHeatmap({ heatmap }: HourHeatmapProps) {
  const { days, hour_buckets: buckets, peak } = heatmap;
  const max = Math.max(1, ...days.flat());
  const cols = { gridTemplateColumns: `repeat(${buckets.length}, minmax(0, 1fr))` };

  return (
    <div className="flex items-start gap-3">
      <div className="grid gap-1 pt-6" aria-hidden="true">
        {DAY_LABELS.slice(0, days.length).map((d) => (
          <div key={d} className="t-micro ink-muted flex h-7 items-center">
            {d}
          </div>
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 grid gap-1" style={cols} aria-hidden="true">
          {buckets.map((b) => (
            <div key={b} className="t-micro ink-muted text-center">
              {b}
            </div>
          ))}
        </div>
        <div
          className="grid gap-1"
          role="img"
          aria-label={
            peak
              ? `Engagement by day of week and hour. Peak: ${DAY_LABELS[peak.day] ?? ""} around ${buckets[peak.bucket] ?? ""}.`
              : "Engagement by day of week and hour."
          }
        >
          {days.map((row, di) => (
            <div key={di} className="grid gap-1" style={cols}>
              {row.map((v, hi) => {
                const isPeak = peak !== null && peak.day === di && peak.bucket === hi;
                return (
                  <div
                    key={hi}
                    className={cn(
                      "relative h-7 rounded-md",
                      isPeak && "ring-2 ring-terra-500",
                    )}
                    style={{ background: sage(Math.max(0.05, v / max)) }}
                  >
                    {isPeak && (
                      <span className="t-micro absolute inset-0 flex items-center justify-center font-semibold text-white">
                        ★
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="t-micro ink-muted mt-2 flex items-center justify-between">
          <span>Lower engagement</span>
          <div className="flex gap-0.5" aria-hidden="true">
            {LEGEND_STEPS.map((v) => (
              <div
                key={v}
                className="h-3 w-4 rounded-sm"
                style={{ background: sage(v) }}
              />
            ))}
          </div>
          <span>Higher</span>
        </div>
      </div>
    </div>
  );
}
