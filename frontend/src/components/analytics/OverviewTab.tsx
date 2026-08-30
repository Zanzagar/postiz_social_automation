import { Leaf } from "lucide-react";

import { EmptyState } from "@/components/pasture";
import { platformBy } from "@/lib/platforms";
import type { AnalyticsSummary } from "@/lib/api";
import { AreaChart } from "./AreaChart";
import { InsightCard } from "./InsightCard";
import { KpiCard } from "./KpiCard";
import { TabError, TabLoading } from "./TabFallbacks";
import {
  CHART_PRIOR,
  CHART_SAGE,
  compactNumber,
  formatDelta,
  formatRate,
  rangeMeta,
  shortDate,
} from "./format";

interface OverviewTabProps {
  data: AnalyticsSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  range: string;
}

function TopPostCard({ post }: { post: NonNullable<AnalyticsSummary["top_post"]> }) {
  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-sage-800 to-sage-700 p-5 text-cream-100">
      <div className="absolute -top-8 -right-8 opacity-10" aria-hidden="true">
        <Leaf size={140} strokeWidth={1} />
      </div>
      <div className="t-label text-cream-200/80">Top post</div>
      <div className="t-title mt-2 leading-snug">“{post.title}”</div>
      <div className="t-caption mt-1 text-cream-200/70">
        {platformBy(post.platform).label} · {shortDate(post.date)}
        {post.pillar ? ` · pillar: ${post.pillar}` : ""}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 border-t border-sage-600/40 pt-4">
        {[
          [compactNumber(post.likes), "Likes"],
          [compactNumber(post.comments), "Comments"],
          [formatRate(post.rate), "Eng rate"],
        ].map(([value, label]) => (
          <div key={label}>
            <div className="t-h2 font-serif">{value}</div>
            <div className="t-micro tracking-wider text-cream-200/70 uppercase">
              {label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Overview — KPI row, headline chart, top post, and Claude's insights. */
export function OverviewTab({ data, isLoading, isError, range }: OverviewTabProps) {
  if (isLoading) return <TabLoading />;
  if (isError || !data) return <TabError />;

  const meta = rangeMeta(range);
  const { kpis, engagement_by_day: byDay, top_post: topPost, insights, sources } = data;
  const hasChart =
    byDay.current.length >= 2 && byDay.current.some((p) => p.value > 0);
  // "All time" has no prior period — hide the legend entry and drop the
  // comparison claim from the chart's aria-label.
  const isAllTime = meta.id === "all";
  // Reach comes only from imported platform analytics — 0/null means "not
  // imported yet", never "nobody was reached".
  const reachMissing = !kpis.reach.value;
  // Avg rate needs that reach to compute — null means "unknowable", never
  // "0% engagement".
  const rateMissing = kpis.avg_rate.value == null;

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Posts published"
          value={kpis.posts.value.toLocaleString()}
          delta={formatDelta(kpis.posts.delta_pct)}
          series={kpis.posts.series}
          accent="sage"
        />
        <KpiCard
          label="Total engagement"
          value={compactNumber(kpis.engagement.value)}
          delta={formatDelta(kpis.engagement.delta_pct)}
          series={kpis.engagement.series}
          accent="sage"
        />
        <div title={rateMissing ? "Needs reach data to compute" : undefined}>
          <KpiCard
            label="Avg. engagement rate"
            value={rateMissing ? "—" : formatRate(kpis.avg_rate.value)}
            delta={formatDelta(kpis.avg_rate.delta_pct)}
            series={kpis.avg_rate.series}
            accent="terra"
          />
        </div>
        <div title={reachMissing ? "No reach data imported yet" : undefined}>
          <KpiCard
            label="Total reach"
            value={reachMissing ? "—" : compactNumber(kpis.reach.value)}
            delta={formatDelta(kpis.reach.delta_pct)}
            series={kpis.reach.series}
            accent="cream"
          />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="bg-card border-hair shadow-card min-w-0 rounded-xl p-5">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="t-label text-sage-600 dark:text-sage-300">
                Engagement by day
              </div>
              <div className="t-h2 mt-0.5 text-sage-800 dark:text-sage-100">
                How the days unfolded
              </div>
            </div>
            <div className="t-caption ink-muted flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: CHART_SAGE }}
                  aria-hidden="true"
                />
                This period
              </span>
              {!isAllTime && (
                <span className="flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: CHART_PRIOR }}
                    aria-hidden="true"
                  />
                  Prior {meta.window}
                </span>
              )}
            </div>
          </div>
          {hasChart ? (
            <AreaChart
              current={byDay.current}
              previous={byDay.previous}
              ariaLabel={isAllTime ? "Engagement by day" : undefined}
            />
          ) : (
            <EmptyState
              icon={Leaf}
              title="Nothing to chart yet"
              body="Engagement will take root here once your posts have been out in the field a little while."
            />
          )}
        </div>

        {topPost ? (
          <TopPostCard post={topPost} />
        ) : (
          <div className="bg-card border-hair shadow-card rounded-xl">
            <EmptyState
              icon={Leaf}
              title="No standout post yet"
              body="When one of your posts leads the herd, it will be honored here."
            />
          </div>
        )}
      </div>

      {insights.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {insights.map((ins, i) => (
            <InsightCard key={i} {...ins} />
          ))}
        </div>
      )}

      {sources.history > 0 && (
        <p className="t-caption ink-muted">Includes imported Facebook history.</p>
      )}
    </div>
  );
}
