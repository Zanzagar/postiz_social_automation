import { ArrowDown, ArrowUp } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { SkeletonText, TextLink } from "@/components/pasture";
import type { AnalyticsOverview, AnalyticsSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import { DashCard } from "./DashCard";

const SAGE = "#4a7c59"; // brand sage-500 — chart stroke per design

/** "8,412" below 10k; "34.2k" / "1.2m" above — the design's compact numerals. */
function formatCompact(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${trimTrailingZero(n / 1_000_000)}m`;
  if (abs >= 10_000) return `${trimTrailingZero(n / 1_000)}k`;
  return n.toLocaleString();
}

function trimTrailingZero(value: number): string {
  const fixed = value.toFixed(1);
  return fixed.endsWith(".0") ? fixed.slice(0, -2) : fixed;
}

function Sparkline({ values, label }: { values: number[]; label: string }) {
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
      aria-label={label}
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

/** "+24% vs last" / "-8%" line under a KPI tile. Render only with a real delta. */
function DeltaLine({
  pct,
  suffix = "",
  className,
}: {
  pct: number;
  suffix?: string;
  className?: string;
}) {
  const Icon = pct < 0 ? ArrowDown : ArrowUp;
  const rounded = Math.round(pct);
  const text = `${rounded > 0 ? "+" : ""}${rounded}%${suffix}`;
  return (
    <div className={cn("t-caption mt-1 flex items-center gap-0.5", className)}>
      <Icon size={11} strokeWidth={1.75} aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

/** Real 7-day KPIs from /api/analytics/summary. */
function SummaryPulse({ summary }: { summary: AnalyticsSummary }) {
  const { engagement, reach } = summary.kpis;
  const top = summary.top_post;
  return (
    <>
      <div className="mb-3 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-sage-100 bg-sage-50 p-3 dark:border-sage-700 dark:bg-sage-800">
          <div className="t-label text-sage-700/80 dark:text-sage-200/80">
            Engagement
          </div>
          <div className="t-h2 mt-1 leading-none text-sage-800 dark:text-sage-100">
            {formatCompact(engagement.value)}
          </div>
          {engagement.delta_pct != null && (
            <DeltaLine
              pct={engagement.delta_pct}
              suffix=" vs last"
              className="text-sage-500 dark:text-sage-300"
            />
          )}
        </div>
        <div className="rounded-xl border border-terra-200 bg-terra-50 p-3 dark:border-terra-600 dark:bg-terra-700/30">
          <div className="t-label text-terra-700/80 dark:text-terra-200/80">Reach</div>
          <div className="t-h2 mt-1 leading-none text-terra-800 dark:text-terra-100">
            {formatCompact(reach.value)}
          </div>
          {reach.delta_pct != null && (
            <DeltaLine
              pct={reach.delta_pct}
              className="text-terra-600 dark:text-terra-300"
            />
          )}
        </div>
      </div>
      <Sparkline
        values={engagement.series}
        label="Engagement per day, last 7 days"
      />
      <div className="t-caption ink-muted mt-2">
        engagement per day · last 7 days
      </div>
      {top && (
        <div className="t-caption ink-muted mt-2 flex min-w-0 items-baseline whitespace-nowrap">
          <span className="shrink-0">Best post:&nbsp;</span>
          <span className="truncate font-medium text-sage-700 dark:text-sage-300">
            {top.title}
          </span>
          <span className="shrink-0">
            &nbsp;· {formatCompact(top.engagement)} engagements
          </span>
        </div>
      )}
    </>
  );
}

/** Legacy posted-count pulse — shown when the summary errors or has no data. */
function FallbackPulse({
  overview,
  series,
}: {
  overview?: AnalyticsOverview;
  series: number[];
}) {
  return (
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
      <Sparkline values={series} label="Posts per day, last 14 days" />
      <div className="t-caption ink-muted mt-2">posts per day · last 14 days</div>
    </>
  );
}

interface PulseCardProps {
  /** 7-day analytics summary; the card's primary data source */
  summary?: AnalyticsSummary;
  /** true when the summary query failed — forces the fallback view */
  summaryError?: boolean;
  /** legacy overview totals, used by the fallback view */
  overview?: AnalyticsOverview;
  /** posts-per-day fallback series (last 14 days) */
  series: number[];
  isLoading?: boolean;
}

/** "This week's pulse" — engagement/reach KPIs with deltas and a sparkline. */
export function PulseCard({
  summary,
  summaryError,
  overview,
  series,
  isLoading,
}: PulseCardProps) {
  const navigate = useNavigate();
  const hasSummary =
    !summaryError &&
    summary != null &&
    summary.sources.app + summary.sources.history > 0;

  return (
    <DashCard
      title="This week's pulse"
      right={
        <TextLink
          href="/analytics"
          className="t-caption"
          onClick={(e) => {
            e.preventDefault();
            navigate("/analytics");
          }}
        >
          See analytics →
        </TextLink>
      }
    >
      {isLoading ? (
        <SkeletonText lines={3} />
      ) : hasSummary ? (
        <SummaryPulse summary={summary} />
      ) : (
        <FallbackPulse overview={overview} series={series} />
      )}
    </DashCard>
  );
}
