import { ExternalLink, Eye, FileText } from "lucide-react";

import type { KnowledgeStats } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyState, SkeletonText } from "@/components/pasture";

const UNCLASSIFIED = "Unclassified";

interface InsightsTabProps {
  stats?: KnowledgeStats;
  isLoading: boolean;
  /** True when the stats fetch failed — render an honest error, not "no insights". */
  isError?: boolean;
}

export function InsightsTab({ stats, isLoading, isError }: InsightsTabProps) {
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Loading insights"
        className="grid gap-4 px-4 py-5 sm:px-8 md:grid-cols-3"
      >
        {[0, 1, 2].map((i) => (
          <div key={i} className="bg-card border-hair rounded-xl p-4">
            <SkeletonText lines={5} />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    // A failed fetch is not an empty library — no call-to-action here.
    return (
      <EmptyState
        title="Couldn't load this right now"
        body="Try again in a moment."
      />
    );
  }

  if (!stats || stats.total_knowledge === 0) {
    return (
      <EmptyState
        title="No insights yet"
        body="Once Claude has read the sites, fact-type, pillar, and topic breakdowns show up here."
      />
    );
  }

  const byType = [...stats.by_type].sort((a, b) => b.count - a.count);
  const byPillar = [...stats.by_pillar]
    .map((r) => ({ label: r.pillar ?? "Unassigned", count: r.count }))
    .sort((a, b) => b.count - a.count);
  const byTopic = [...stats.by_topic]
    .map((r) => ({ label: r.topic ?? UNCLASSIFIED, count: r.count }))
    .sort((a, b) => b.count - a.count);
  const topTopics = byTopic.slice(0, 8);
  const unclassified = byTopic.find((t) => t.label === UNCLASSIFIED);

  return (
    <div className="grid gap-4 px-4 py-5 sm:px-8 md:grid-cols-3">
      <BarCard
        title="By fact type"
        sub="What kind of facts Claude extracted"
        rows={byType.map((r) => ({ label: r.type, count: r.count }))}
        barClass="bg-sage-500"
        capitalize
      />
      <BarCard
        title="By pillar"
        sub="Which pillars are well-fed"
        rows={byPillar}
        barClass="bg-terra-500"
      />

      {/* Topics list */}
      <section
        aria-label="Facts by topic"
        className="bg-card border-hair shadow-card rounded-xl p-4"
      >
        <div className="t-label text-sage-700 dark:text-sage-300">By topic</div>
        <p className="t-caption ink-muted mt-0.5">
          Top {topTopics.length} of {byTopic.length}
        </p>
        <div className="mt-3 space-y-1">
          {topTopics.map((r) => (
            <div
              key={r.label}
              className="t-caption border-hair-b flex items-center justify-between py-1 last:border-b-0"
            >
              <span
                className={cn(
                  r.label === UNCLASSIFIED
                    ? "text-terra-700 dark:text-terra-200"
                    : "ink",
                )}
              >
                {r.label}
              </span>
              <span className="font-mono font-semibold text-sage-800 dark:text-sage-100">
                {r.count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
        {unclassified && (
          <div className="t-caption mt-2.5 flex items-center gap-1.5 border-t border-sage-100 pt-2.5 text-terra-700 dark:border-sage-700 dark:text-terra-200">
            <Eye size={11} strokeWidth={1.75} aria-hidden="true" />
            {unclassified.count.toLocaleString()} facts haven't been topic-classified yet
          </div>
        )}
      </section>

      {/* Coverage gaps */}
      <section
        aria-label="Coverage gaps"
        className="rounded-xl border border-cream-300 bg-cream-100/60 p-4 md:col-span-3 dark:border-cream-400/40 dark:bg-cream-400/10"
      >
        <div className="flex items-center gap-2">
          <Eye size={13} strokeWidth={1.75} aria-hidden="true" className="text-cream-ink" />
          <div className="t-label text-cream-ink">Coverage gaps</div>
        </div>
        {stats.coverage_gaps.length === 0 ? (
          <p className="t-body-sm text-cream-ink-deep mt-1 leading-relaxed">
            No gaps — every crawled page yielded at least one fact.
          </p>
        ) : (
          <>
            <p className="t-body-sm text-cream-ink-deep mt-1 leading-relaxed">
              These pages have text but Claude extracted zero facts from them — usually
              thin, repetitive, or image-heavy pages. Worth a look.
            </p>
            <div className="mt-3 space-y-1.5">
              {stats.coverage_gaps.map((gap) => (
                <div
                  key={gap.url}
                  className="bg-card t-body-sm flex items-center gap-2 rounded-lg border border-cream-300 px-3 py-2 dark:border-cream-400/40"
                >
                  <FileText
                    size={11}
                    strokeWidth={1.75}
                    aria-hidden="true"
                    className="text-cream-ink shrink-0"
                  />
                  <span className="ink truncate font-medium">{gap.title}</span>
                  <span className="t-caption ink-muted shrink-0">{gap.site}</span>
                  <a
                    href={gap.url}
                    target="_blank"
                    rel="noreferrer"
                    className="fr t-caption ml-auto flex shrink-0 items-center gap-1 rounded text-sage-600 hover:underline dark:text-sage-300"
                  >
                    <ExternalLink size={10} strokeWidth={1.75} aria-hidden="true" />
                    view page
                  </a>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

interface BarCardProps {
  title: string;
  sub: string;
  rows: Array<{ label: string; count: number }>;
  barClass: string;
  capitalize?: boolean;
}

function BarCard({ title, sub, rows, barClass, capitalize }: BarCardProps) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <section
      aria-label={`Facts ${title.toLowerCase()}`}
      className="bg-card border-hair shadow-card rounded-xl p-4"
    >
      <div className="t-label text-sage-700 dark:text-sage-300">{title}</div>
      <p className="t-caption ink-muted mt-0.5">{sub}</p>
      <div className="mt-3 space-y-2">
        {rows.map((r) => (
          <div key={r.label}>
            <div className="t-caption flex items-center justify-between">
              <span className={cn("ink", capitalize && "capitalize")}>{r.label}</span>
              <span className="font-mono font-semibold text-sage-800 dark:text-sage-100">
                {r.count.toLocaleString()}
              </span>
            </div>
            <div
              className="mt-1 h-1.5 overflow-hidden rounded-full bg-sage-50 dark:bg-sage-800"
              aria-hidden="true"
            >
              <div
                className={cn("h-full", barClass)}
                style={{ width: `${(r.count / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
