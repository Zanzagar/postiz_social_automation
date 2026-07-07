import { Wheat } from "lucide-react";

import { cn } from "@/lib/utils";
import { SkeletonText } from "@/components/pasture";
import type { DashboardStats } from "@/hooks/useDashboardData";

interface RitualStripProps {
  stats: DashboardStats;
  isLoading?: boolean;
}

/** Four serif stat tiles — the morning ritual strip. */
export function RitualStrip({ stats, isLoading }: RitualStripProps) {
  const tiles = [
    {
      key: "posted",
      value: stats.postedToday,
      label: stats.postedToday === 1 ? "post gone out" : "posts gone out",
      sub: stats.lastPostedTime ? `last at ${stats.lastPostedTime}` : "quiet so far",
      highlight: false,
    },
    {
      key: "review",
      value: stats.awaitingReview,
      label: "awaiting your review",
      sub:
        stats.awaitingReview > 0
          ? `across ${stats.pendingPlatformCount} platform${stats.pendingPlatformCount === 1 ? "" : "s"}`
          : "nothing waiting",
      highlight: true,
    },
    {
      key: "scheduled",
      value: stats.scheduledToday,
      label: "scheduled today",
      sub: stats.nextReleaseTime ? `next at ${stats.nextReleaseTime}` : "no auto-releases",
      highlight: false,
    },
    {
      key: "streak",
      value: stats.dayStreak,
      label: "day streak",
      sub: stats.dayStreak > 0 ? "and counting" : "start one today",
      highlight: false,
    },
  ];

  return (
    <div className="paper relative overflow-hidden rounded-2xl border border-cream-200 bg-gradient-to-br from-cream-100 via-[var(--surface-card)] to-sage-50 p-5 dark:border-sage-700 dark:from-sage-800 dark:via-[var(--surface-card)] dark:to-sage-800">
      <div className="absolute top-5 right-5 opacity-20" aria-hidden="true">
        <Wheat size={64} strokeWidth={1.75} className="text-sage-500" />
      </div>
      {isLoading ? (
        <SkeletonText lines={2} />
      ) : (
        <div className="relative grid grid-cols-2 gap-4 sm:grid-cols-4">
          {tiles.map((tile, i) => (
            <div
              key={tile.key}
              className={cn(
                "min-w-0 pl-4 border-sage-100 dark:border-sage-700",
                // 2x2 on mobile: only the second column gets a divider;
                // 4-up from sm: every tile after the first gets one.
                i % 2 === 1 && "border-l",
                i > 0 && "sm:border-l",
              )}
            >
              <div
                data-testid={`stat-${tile.key}`}
                className={cn(
                  "t-display",
                  tile.highlight ? "text-terra-600 dark:text-terra-300" : "text-sage-800 dark:text-sage-100",
                )}
              >
                {tile.value}
              </div>
              <div className="t-body-sm ink mt-1">{tile.label}</div>
              <div className="t-caption ink-muted mt-0.5">{tile.sub}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
