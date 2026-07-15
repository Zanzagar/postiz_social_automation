import { Sprout } from "lucide-react";

import { EmptyState } from "@/components/pasture";
import { pillarColor } from "@/lib/pillars";
import type { Insight, PillarInsightRow } from "@/lib/api";
import { InsightCard } from "./InsightCard";
import { TabError, TabLoading } from "./TabFallbacks";
import { formatRate } from "./format";

interface PillarsTabProps {
  pillars: PillarInsightRow[];
  insights: Insight[];
  isLoading: boolean;
  isError: boolean;
}

function clampPct(v: number): number {
  return Math.min(Math.max(v, 0), 100);
}

function PillarCard({ p }: { p: PillarInsightRow }) {
  const color = p.color ?? pillarColor(p.pillar);
  const seriesMax = Math.max(...p.weekly_series, 1);
  return (
    <div className="bg-card border-hair shadow-card rounded-xl p-3.5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span
          className="h-6 w-6 shrink-0 rounded-md"
          style={{ background: color }}
          aria-hidden="true"
        />
        <span className="t-body ink flex-1 font-semibold">{p.pillar}</span>
        <span className="t-caption ink-muted">
          {p.posts} posts · {p.engagement.toLocaleString()} engagement
          {p.rate !== null ? ` · ${formatRate(p.rate)} avg` : ""}
        </span>
      </div>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <div className="t-label mb-1 text-sage-600 dark:text-sage-300">
            Target mix
          </div>
          <div className="bg-warm relative h-2 overflow-hidden rounded-full">
            {p.target_pct !== null && (
              <div
                className="absolute top-0 left-0 h-full rounded-full opacity-30"
                style={{ width: `${clampPct(p.target_pct)}%`, background: color }}
              />
            )}
            <div
              className="absolute top-0 left-0 h-full rounded-full"
              style={{ width: `${clampPct(p.actual_pct)}%`, background: color }}
            />
          </div>
          <div className="t-micro ink-muted mt-0.5 flex justify-between">
            <span>Actual {p.actual_pct}%</span>
            {p.target_pct !== null ? (
              <span>Target {p.target_pct}%</span>
            ) : (
              <span>No target set</span>
            )}
          </div>
        </div>
        <div>
          <div className="t-label mb-1 text-sage-600 dark:text-sage-300">
            Engagement rate
          </div>
          {p.weekly_series.length > 0 ? (
            <>
              <div
                className="flex h-6 items-end gap-0.5"
                role="img"
                aria-label={`${p.pillar} weekly engagement, oldest to newest`}
              >
                {p.weekly_series.map((v, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm"
                    style={{
                      height: `${Math.max(8, (v / seriesMax) * 100)}%`,
                      background: color,
                      opacity: 0.4 + 0.6 * (v / seriesMax),
                    }}
                  />
                ))}
              </div>
              <div className="t-micro ink-muted mt-0.5 flex justify-between">
                <span>12 weeks ago</span>
                <span>this week</span>
              </div>
            </>
          ) : (
            <p className="t-micro ink-muted">Not enough history yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/** Per pillar — target-mix bars, weekly mini charts, and Claude's insights. */
export function PillarsTab({ pillars, insights, isLoading, isError }: PillarsTabProps) {
  if (isLoading) return <TabLoading />;
  if (isError) return <TabError />;
  if (pillars.length === 0) {
    return (
      <EmptyState
        icon={Sprout}
        title="No pillar activity yet"
        body="As posts gather under each pillar, their balance and results will show here."
      />
    );
  }

  return (
    <div
      className={
        insights.length > 0
          ? "grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]"
          : undefined
      }
    >
      <div className="min-w-0">
        <h3 className="t-h2 mb-3 text-sage-800 dark:text-sage-100">
          Which pillars fed the feed
        </h3>
        <div className="space-y-2">
          {pillars.map((p) => (
            <PillarCard key={p.pillar} p={p} />
          ))}
        </div>
      </div>
      {insights.length > 0 && (
        <aside className="space-y-3">
          {insights.map((ins, i) => (
            <InsightCard key={i} {...ins} />
          ))}
        </aside>
      )}
    </div>
  );
}
