import { useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Download, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { api, type AnalyticsPostRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader, PastureTabs, SegmentedControl } from "@/components/pasture";
import { OverviewTab } from "@/components/analytics/OverviewTab";
import { PostsTab } from "@/components/analytics/PostsTab";
import { PillarsTab } from "@/components/analytics/PillarsTab";
import { PlatformsTab } from "@/components/analytics/PlatformsTab";
import { RhythmTab } from "@/components/analytics/RhythmTab";
import { RANGES, buildResultsCsv } from "@/components/analytics/format";

const POSTS_PAGE_SIZE = 20;
/** Cap for the on-demand export fetch when the posts tab hasn't loaded. */
const EXPORT_FETCH_LIMIT = 500;

const TAB_ITEMS = [
  { id: "overview", label: "Overview" },
  { id: "posts", label: "Per post" },
  { id: "pillars", label: "Per pillar" },
  { id: "platforms", label: "Per platform" },
  { id: "rhythm", label: "Rhythm" },
];

const RANGE_OPTIONS = RANGES.map((r) => ({ id: r.id, label: r.label }));

function downloadCsv(rows: AnalyticsPostRow[], range: string) {
  const blob = new Blob([buildResultsCsv(rows)], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gita-valley-results-${range}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Results (analytics) — Overview / Per post / Per pillar / Per platform / Rhythm. */
export function AnalyticsPage() {
  const [tab, setTab] = useState("overview");
  const [range, setRange] = useState("30d");

  const summaryQ = useQuery({
    queryKey: ["analytics", "summary", range],
    queryFn: () => api.getAnalyticsSummary(range),
    enabled: tab === "overview",
  });

  const postsQ = useInfiniteQuery({
    queryKey: ["analytics", "posts", range],
    queryFn: ({ pageParam }) => api.getAnalyticsPosts(range, POSTS_PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, all) => {
      const shown = all.reduce((n, page) => n + page.posts.length, 0);
      return shown < last.total ? shown : undefined;
    },
    enabled: tab === "posts",
  });

  const pillarsQ = useQuery({
    queryKey: ["analytics", "pillar-insights", range],
    queryFn: () => api.getAnalyticsPillarInsights(range),
    enabled: tab === "pillars",
  });

  const platformsQ = useQuery({
    queryKey: ["analytics", "platforms", range],
    queryFn: () => api.getAnalyticsPlatforms(range),
    enabled: tab === "platforms",
  });

  const rhythmQ = useQuery({
    queryKey: ["analytics", "rhythm", range],
    queryFn: () => api.getAnalyticsRhythm(range),
    enabled: tab === "rhythm",
  });

  const postRows = postsQ.data?.pages.flatMap((p) => p.posts) ?? [];
  const postsTotal = postsQ.data?.pages[0]?.total ?? 0;

  const handleExport = async () => {
    try {
      let rows = postRows;
      if (rows.length === 0) {
        const res = await api.getAnalyticsPosts(range, EXPORT_FETCH_LIMIT, 0);
        rows = res.posts;
      }
      downloadCsv(rows, range);
    } catch {
      toast.error("Couldn't export results right now");
    }
  };

  const now = new Date();
  const greeting = `${now.toLocaleDateString(undefined, { weekday: "long" })} · ${now.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  return (
    <div>
      <PageHeader
        greeting={greeting}
        title="Results"
        subtitle="How your pasture fed the feed this month."
        icon={TrendingUp}
        right={
          <>
            <SegmentedControl
              aria-label="Time range"
              options={RANGE_OPTIONS}
              value={range}
              onChange={setRange}
            />
            <Button
              variant="outline"
              size="sm"
              className="fr"
              onClick={() => void handleExport()}
            >
              <Download size={13} strokeWidth={1.75} aria-hidden="true" />
              Export CSV
            </Button>
          </>
        }
      />

      <div className="border-hair-b px-4 sm:px-8">
        <PastureTabs
          aria-label="Analytics views"
          items={TAB_ITEMS}
          value={tab}
          onChange={setTab}
          className="gap-3"
        />
      </div>

      <div className="mx-auto w-full max-w-[1180px] px-4 py-6 sm:px-8">
        {tab === "overview" && (
          <OverviewTab
            data={summaryQ.data}
            isLoading={summaryQ.isPending}
            isError={summaryQ.isError}
            range={range}
          />
        )}
        {tab === "posts" && (
          <PostsTab
            rows={postRows}
            total={postsTotal}
            isLoading={postsQ.isPending}
            isError={postsQ.isError}
            hasMore={postsQ.hasNextPage}
            isFetchingMore={postsQ.isFetchingNextPage}
            onShowMore={() => void postsQ.fetchNextPage()}
          />
        )}
        {tab === "pillars" && (
          <PillarsTab
            pillars={pillarsQ.data?.pillars ?? []}
            insights={pillarsQ.data?.insights ?? []}
            isLoading={pillarsQ.isPending}
            isError={pillarsQ.isError}
          />
        )}
        {tab === "platforms" && (
          <PlatformsTab
            platforms={platformsQ.data?.platforms ?? []}
            heatmap={platformsQ.data?.heatmap}
            isLoading={platformsQ.isPending}
            isError={platformsQ.isError}
            range={range}
          />
        )}
        {tab === "rhythm" && (
          <RhythmTab
            weeks={rhythmQ.data?.weeks ?? []}
            festivals={rhythmQ.data?.festivals ?? []}
            season={rhythmQ.data?.season}
            isLoading={rhythmQ.isPending}
            isError={rhythmQ.isError}
            range={range}
          />
        )}
      </div>
    </div>
  );
}
