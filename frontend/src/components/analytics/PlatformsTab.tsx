import { Clock, Sprout } from "lucide-react";

import { EmptyState, PlatformDot } from "@/components/pasture";
import { platformBy } from "@/lib/platforms";
import type { AnalyticsHeatmap, PlatformStatRow } from "@/lib/api";
import { HourHeatmap } from "./HourHeatmap";
import { TabError, TabLoading } from "./TabFallbacks";
import { formatRate, rangeMeta } from "./format";

interface PlatformsTabProps {
  platforms: PlatformStatRow[];
  heatmap: AnalyticsHeatmap | undefined;
  isLoading: boolean;
  isError: boolean;
  range: string;
}

function PlatformCard({ p }: { p: PlatformStatRow }) {
  return (
    <div className="bg-card border-hair shadow-card rounded-xl p-4">
      <div className="mb-3 flex items-center gap-2">
        <PlatformDot id={p.platform} size={14} />
        <span className="t-ui ink font-semibold">{platformBy(p.platform).label}</span>
      </div>
      <div className="t-h2 leading-none text-sage-800 dark:text-sage-100">
        {formatRate(p.rate)}
      </div>
      <div className="t-caption ink-muted mt-1">engagement rate</div>
      <div className="t-caption ink-muted mt-3 space-y-1 border-t border-sage-50 pt-3 dark:border-sage-800">
        <div className="flex justify-between gap-2">
          <span>Posts</span>
          <span className="ink font-mono">{p.posts.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-2">
          <span>Reach</span>
          <span className="ink font-mono">{p.reach.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-2">
          <span>Engagement</span>
          <span className="ink font-mono">{p.engagement.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

/** Per platform — stat cards plus the best-time-to-post heatmap. */
export function PlatformsTab({
  platforms,
  heatmap,
  isLoading,
  isError,
  range,
}: PlatformsTabProps) {
  if (isLoading) return <TabLoading />;
  if (isError || !heatmap) return <TabError />;

  const meta = rangeMeta(range);

  return (
    <div className="space-y-5">
      {platforms.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {platforms.map((p) => (
            <PlatformCard key={p.platform} p={p} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Sprout}
          title="No platform results yet"
          body="Once posts have been out on your platforms in this window, their numbers will settle in here."
        />
      )}

      <div className="bg-card border-hair shadow-card rounded-xl p-5">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="t-label text-sage-600 dark:text-sage-300">
              Best time to post
            </div>
            <div className="t-h2 mt-0.5 text-sage-800 dark:text-sage-100">
              The week's engagement terrain
            </div>
          </div>
          <div className="t-caption ink-muted">
            {range === "all"
              ? "From your full posting history"
              : `From your last ${meta.window}`}{" "}
            · based on {heatmap.sample_size} posts
          </div>
        </div>
        {heatmap.sample_size === 0 ? (
          <EmptyState
            icon={Clock}
            title="Not enough posting history yet"
            body="Once a few more posts are out grazing, the week's warmest hours will show here."
          />
        ) : (
          <HourHeatmap heatmap={heatmap} />
        )}
      </div>
    </div>
  );
}
