import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Eye, Globe, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader, PastureTabs } from "@/components/pasture";
import { KMetric } from "@/components/knowledge/KMetric";
import { CrawlBanner } from "@/components/knowledge/CrawlBanner";
import { FactsTab } from "@/components/knowledge/FactsTab";
import { SourcesTab } from "@/components/knowledge/SourcesTab";
import { InsightsTab } from "@/components/knowledge/InsightsTab";
import { GraphTab } from "@/components/knowledge/GraphTab";
import { AskSheet } from "@/components/knowledge/AskSheet";

const TABS = [
  { id: "facts", label: "Facts & search" },
  { id: "sources", label: "Sources" },
  { id: "insights", label: "Insights" },
  { id: "graph", label: "Graph" },
];

export function KnowledgePage() {
  const [tab, setTab] = useState("facts");
  const [askOpen, setAskOpen] = useState(false);
  const queryClient = useQueryClient();

  const status = useQuery({
    queryKey: ["knowledge", "status"],
    queryFn: () => api.getKnowledgeStatus(),
  });

  const stats = useQuery({
    queryKey: ["knowledge", "stats"],
    queryFn: () => api.getKnowledgeStats(),
  });

  const pillarsQuery = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
    staleTime: 60_000,
  });

  // Poll only while a crawl is running (same pattern as the legacy KnowledgeStatus card).
  const progress = useQuery({
    queryKey: ["knowledge", "progress"],
    queryFn: () => api.getCrawlProgress(),
    refetchInterval: (query) => (query.state.data?.running ? 2000 : false),
  });

  const crawlRunning = progress.data?.running ?? false;

  // When a crawl finishes (running flips true → false), the metrics and fact
  // lists are stale — refetch everything under the "knowledge" key.
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !crawlRunning) {
      void queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    }
    wasRunning.current = crawlRunning;
  }, [crawlRunning, queryClient]);

  const crawlMutation = useMutation({
    mutationFn: () => api.triggerCrawl(),
    onSuccess: (res) => {
      if (res.status === "already_running") {
        toast.info("A crawl is already running");
      } else {
        toast.success("Re-crawl started — Claude is reading the sites");
      }
      void queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: () => toast.error("Couldn't start the crawl"),
  });

  const sources = useMemo(() => status.data?.sources ?? [], [status.data]);
  const webSources = sources.filter((s) => s.type === "web");
  const socialSources = sources.filter((s) => s.type === "social");

  const pagesIndexed = webSources.reduce((sum, s) => sum + (s.page_count ?? 0), 0);
  const postsImported = socialSources.reduce((sum, s) => sum + (s.post_count ?? 0), 0);
  const topTypes = [...(stats.data?.by_type ?? [])]
    .sort((a, b) => b.count - a.count)
    .slice(0, 4)
    .map((t) => t.type);
  // coverage_gaps is capped server-side (10) — prefer the true count when sent.
  const gapCount =
    stats.data?.coverage_gap_count ?? stats.data?.coverage_gaps.length ?? 0;
  const metricsLoading = status.isLoading || stats.isLoading;

  return (
    <div>
      <PageHeader
        greeting="Knowledge"
        title="What Claude has read"
        subtitle="Facts extracted from gitavalley.org, iskcongitanagari.org, and your Facebook history."
        icon={BookOpen}
        right={
          <>
            <Button
              variant="outline"
              size="sm"
              className="fr"
              onClick={() => setAskOpen(true)}
            >
              <Sparkles size={13} strokeWidth={1.75} aria-hidden="true" />
              Ask what it knows
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="fr"
              onClick={() => crawlMutation.mutate()}
              disabled={crawlMutation.isPending || crawlRunning}
            >
              <RefreshCw size={13} strokeWidth={1.75} aria-hidden="true" />
              Re-crawl
            </Button>
          </>
        }
      />

      <CrawlBanner progress={progress.data} />

      {/* Metric strip — from GET /status + /stats */}
      <div className="border-hair-b grid grid-cols-2 gap-3 px-4 pt-4 pb-3 sm:px-8 lg:grid-cols-4">
        <KMetric
          label="Pages indexed"
          value={pagesIndexed.toLocaleString()}
          sub={
            webSources.length > 0
              ? webSources.map((s) => `${s.name} (${s.page_count ?? 0})`).join(" · ")
              : "no websites crawled yet"
          }
          icon={Globe}
          loading={metricsLoading}
        />
        <KMetric
          label="Facts extracted"
          value={(status.data?.knowledge_entries ?? 0).toLocaleString()}
          sub={topTypes.length > 0 ? topTypes.join(" · ") : undefined}
          icon={Sparkles}
          loading={metricsLoading}
        />
        <KMetric
          label="Posts imported"
          value={postsImported.toLocaleString()}
          sub={
            socialSources.length > 0
              ? socialSources.map((s) => `${s.name} ${s.post_count ?? 0}`).join(" · ")
              : "no social history yet"
          }
          icon={MessageSquare}
          loading={metricsLoading}
        />
        <KMetric
          label="Coverage gaps"
          value={gapCount.toLocaleString()}
          sub="pages with zero extracted facts"
          icon={Eye}
          warn={gapCount > 0}
          loading={metricsLoading}
        />
      </div>

      {/* Section tabs */}
      <div className="border-hair-b px-4 pt-2 sm:px-8">
        <PastureTabs
          variant="underline"
          aria-label="Knowledge sections"
          items={TABS}
          value={tab}
          onChange={setTab}
        />
      </div>

      {tab === "facts" && (
        <FactsTab
          pillars={pillarsQuery.data ?? []}
          stats={stats.data}
          sources={sources}
        />
      )}
      {tab === "sources" && (
        <SourcesTab
          sources={sources}
          isLoading={status.isLoading}
          isError={status.isError}
          crawlRunning={crawlRunning}
        />
      )}
      {tab === "insights" && (
        <InsightsTab
          stats={stats.data}
          isLoading={stats.isLoading}
          isError={stats.isError}
        />
      )}
      {tab === "graph" && <GraphTab />}

      {askOpen && <AskSheet onClose={() => setAskOpen(false)} />}
    </div>
  );
}
