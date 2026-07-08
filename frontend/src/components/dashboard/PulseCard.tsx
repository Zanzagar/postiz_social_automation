import { SkeletonText } from "@/components/pasture";
import type { AnalyticsOverview } from "@/lib/api";
import { DashCard } from "./DashCard";

const SAGE = "#4a7c59"; // brand sage-500 — chart stroke per design

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const w = 260;
  const h = 44;
  const x = (i: number) => (i / (values.length - 1)) * w;
  const y = (v: number) => h - (v / max) * h;
  const path = values
    .map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h + 4}`}
      className="h-auto w-full"
      role="img"
      aria-label="Posts per day, last 14 days"
    >
      <defs>
        <linearGradient id="gv-pulse-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={SAGE} stopOpacity=".3" />
          <stop offset="1" stopColor={SAGE} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L ${w} ${h} L 0 ${h} Z`} fill="url(#gv-pulse-fill)" />
      <path d={path} stroke={SAGE} strokeWidth="1.5" fill="none" />
      <circle
        cx={x(values.length - 1)}
        cy={y(values[values.length - 1])}
        r={3}
        fill={SAGE}
      />
    </svg>
  );
}

interface PulseCardProps {
  overview?: AnalyticsOverview;
  series: number[];
  isLoading?: boolean;
}

/** "This week's pulse" — engagement/reach tiles and a posts-per-day sparkline. */
export function PulseCard({ overview, series, isLoading }: PulseCardProps) {
  return (
    <DashCard title="This week's pulse">
      {isLoading ? (
        <SkeletonText lines={3} />
      ) : (
        <>
          {overview ? (
            <div className="mb-3 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-sage-100 bg-sage-50 p-3 dark:border-sage-700 dark:bg-sage-800">
                <div className="t-label text-sage-700/80 dark:text-sage-200/80">
                  Engagement
                </div>
                <div className="t-h2 mt-1 leading-none text-sage-800 dark:text-sage-100">
                  {overview.total_engagement.toLocaleString()}
                </div>
                <div className="t-caption mt-1 text-sage-500 dark:text-sage-300">
                  avg {overview.avg_engagement.toLocaleString()} per post
                </div>
              </div>
              <div className="rounded-xl border border-terra-200 bg-terra-50 p-3 dark:border-terra-600 dark:bg-terra-700/30">
                <div className="t-label text-terra-700/80 dark:text-terra-200/80">Reach</div>
                <div className="t-h2 mt-1 leading-none text-terra-800 dark:text-terra-100">
                  {overview.total_reach.toLocaleString()}
                </div>
                <div className="t-caption mt-1 text-terra-600 dark:text-terra-300">
                  {overview.total_impressions.toLocaleString()} impressions
                </div>
              </div>
            </div>
          ) : (
            <p className="t-caption ink-muted mb-3">
              Analytics are still gathering — check back soon.
            </p>
          )}
          <Sparkline values={series} />
          <div className="t-caption ink-muted mt-2">posts per day · last 14 days</div>
        </>
      )}
    </DashCard>
  );
}
