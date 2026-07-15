import { ArrowUp, ChevronDown, Sprout } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState, PlatformDot } from "@/components/pasture";
import { pillarColor } from "@/lib/pillars";
import type { AnalyticsPostRow } from "@/lib/api";
import { TabError, TabLoading } from "./TabFallbacks";
import { formatRate, shortDate } from "./format";

const GRID = "grid grid-cols-[minmax(0,1fr)_140px_130px_90px_100px_80px_100px]";

interface PostsTabProps {
  rows: AnalyticsPostRow[];
  total: number;
  isLoading: boolean;
  isError: boolean;
  hasMore: boolean;
  isFetchingMore: boolean;
  onShowMore: () => void;
}

function TrendCell({ trend }: { trend: AnalyticsPostRow["trend"] }) {
  if (trend === "up") {
    return (
      <span className="t-caption flex items-center gap-0.5 text-sage-600 dark:text-sage-300">
        <ArrowUp size={11} strokeWidth={2} aria-hidden="true" />
        vs avg
      </span>
    );
  }
  if (trend === "down") {
    return (
      <span className="t-caption flex items-center gap-0.5 text-terra-700 dark:text-terra-300">
        <ChevronDown size={11} strokeWidth={2} aria-hidden="true" />
        below
      </span>
    );
  }
  return <span className="t-caption ink-muted">— flat</span>;
}

/** Per post — engagement-sorted table with offset "Show more" pagination. */
export function PostsTab({
  rows,
  total,
  isLoading,
  isError,
  hasMore,
  isFetchingMore,
  onShowMore,
}: PostsTabProps) {
  if (isLoading) return <TabLoading />;
  if (isError) return <TabError />;
  if (rows.length === 0) {
    return (
      <EmptyState
        icon={Sprout}
        title="No posts in this window"
        body="Once posts go out to pasture in this period, their results will gather here."
      />
    );
  }

  return (
    <div>
      <div className="t-body-sm ink-muted mb-3">
        Sorted by engagement · showing {rows.length} of {total}
      </div>
      <div className="bg-card border-hair shadow-card overflow-x-auto rounded-xl">
        <div className="min-w-[860px]">
          <div
            className={`${GRID} border-hair-b t-label h-10 items-center bg-sage-50/60 px-4 text-sage-700 dark:bg-sage-800/60 dark:text-sage-200`}
          >
            <div>Post</div>
            <div>Pillar</div>
            <div>Platforms</div>
            <div>Date</div>
            <div className="text-right">Engagement</div>
            <div className="text-right">Rate</div>
            <div className="text-right">Trend</div>
          </div>
          {rows.map((r, i) => (
            <div
              key={`${r.source}-${r.id ?? "h"}-${i}`}
              className={`${GRID} t-body-sm h-14 items-center border-b border-sage-50 px-4 last:border-0 hover:bg-sage-50/40 dark:border-sage-800 dark:hover:bg-sage-800/40`}
            >
              <div className="ink truncate pr-3">{r.title}</div>
              <div className="flex items-center gap-1.5">
                {r.pillar ? (
                  <>
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ background: pillarColor(r.pillar) }}
                      aria-hidden="true"
                    />
                    <span className="ink-muted truncate">{r.pillar}</span>
                  </>
                ) : (
                  <span className="ink-muted">—</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {r.platforms.map((p) => (
                  <PlatformDot key={p} id={p} size={12} />
                ))}
              </div>
              <div className="t-caption ink-muted">{shortDate(r.date)}</div>
              <div className="ink text-right font-mono">
                {r.engagement.toLocaleString()}
              </div>
              <div className="ink text-right font-mono">{formatRate(r.rate)}</div>
              <div className="flex justify-end">
                <TrendCell trend={r.trend} />
              </div>
            </div>
          ))}
        </div>
      </div>
      {hasMore && (
        <div className="mt-3 flex justify-center">
          <Button
            variant="soft"
            size="sm"
            className="fr"
            onClick={onShowMore}
            disabled={isFetchingMore}
          >
            {isFetchingMore ? "Gathering…" : "Show more"}
          </Button>
        </div>
      )}
    </div>
  );
}
