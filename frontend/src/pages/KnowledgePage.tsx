import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { KnowledgeEntry } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Database,
  FileText,
  BookOpen,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Network,
  Table2,
  Search,
  Globe,
  ExternalLink,
} from "lucide-react";

const FACT_TYPE_COLORS: Record<string, string> = {
  program: "bg-blue-100 text-blue-700",
  event: "bg-purple-100 text-purple-700",
  quote: "bg-amber-100 text-amber-700",
  link: "bg-green-100 text-green-700",
  description: "bg-gray-100 text-gray-700",
};

const PILLAR_COLORS = [
  "bg-sage-100 text-sage-700 border-sage-200",
  "bg-blue-50 text-blue-700 border-blue-200",
  "bg-amber-50 text-amber-700 border-amber-200",
  "bg-purple-50 text-purple-700 border-purple-200",
  "bg-green-50 text-green-700 border-green-200",
  "bg-rose-50 text-rose-700 border-rose-200",
  "bg-orange-50 text-orange-700 border-orange-200",
  "bg-cyan-50 text-cyan-700 border-cyan-200",
];

type ViewMode = "table" | "graph";

export function KnowledgePage() {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [filterTopic, setFilterTopic] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterSite, setFilterSite] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [showGaps, setShowGaps] = useState(false);
  const [searchText, setSearchText] = useState("");

  const stats = useQuery({
    queryKey: ["knowledge", "stats"],
    queryFn: () => api.getKnowledgeStats(),
  });

  const browse = useQuery({
    queryKey: ["knowledge", "browse", filterTopic, filterType, filterSite, currentPage],
    queryFn: () =>
      api.browseKnowledge({
        topic: filterTopic || undefined,
        fact_type: filterType || undefined,
        site: filterSite || undefined,
        page: currentPage,
      }),
  });

  const handleTopicClick = useCallback((topic: string) => {
    setFilterTopic((prev) => (prev === topic ? "" : topic));
    setCurrentPage(1);
  }, []);

  const filteredResults = browse.data?.results.filter((r) =>
    searchText ? r.content.toLowerCase().includes(searchText.toLowerCase()) : true
  ) ?? [];

  const s = stats.data;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sage-800">Knowledge Base</h1>
          <p className="text-sm text-muted-foreground">
            Extracted facts from Gita Valley websites and social media
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border p-1">
          <Button
            size="sm"
            variant={viewMode === "table" ? "default" : "ghost"}
            onClick={() => setViewMode("table")}
          >
            <Table2 className="mr-1 h-4 w-4" />
            Table
          </Button>
          <Button
            size="sm"
            variant={viewMode === "graph" ? "default" : "ghost"}
            onClick={() => setViewMode("graph")}
          >
            <Network className="mr-1 h-4 w-4" />
            Graph
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      {s && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Globe className="h-8 w-8 text-sage-500" />
              <div>
                <p className="text-2xl font-bold">{s.total_pages}</p>
                <p className="text-xs text-muted-foreground">Pages Crawled</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <BookOpen className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{s.total_knowledge}</p>
                <p className="text-xs text-muted-foreground">Knowledge Entries</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <FileText className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">{s.pages_with_knowledge}</p>
                <p className="text-xs text-muted-foreground">Pages Extracted</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <Database className="h-8 w-8 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{s.by_type.length}</p>
                <p className="text-xs text-muted-foreground">Fact Types</p>
              </div>
            </CardContent>
          </Card>
          {s.coverage_gaps.length > 0 && (
            <button onClick={() => setShowGaps(!showGaps)} className="text-left">
              <Card className="border-amber-200 bg-amber-50 transition-all hover:shadow-md">
                <CardContent className="flex items-center gap-3 p-4">
                  <AlertTriangle className="h-8 w-8 text-amber-500" />
                  <div>
                    <p className="text-2xl font-bold">{s.coverage_gaps.length}</p>
                    <p className="text-xs text-amber-700">Coverage Gaps — click to see</p>
                  </div>
                </CardContent>
              </Card>
            </button>
          )}
        </div>
      )}

      {/* Coverage gaps detail */}
      {showGaps && s && s.coverage_gaps.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-amber-800">
              <AlertTriangle className="h-4 w-4" />
              Pages With No Extracted Knowledge
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-amber-700">
              These pages have content but no facts have been extracted yet.
              Re-running "Crawl Websites" will process them.
            </p>
            <div className="space-y-1">
              {s.coverage_gaps.map((gap) => (
                <div key={gap.url} className="flex items-center justify-between rounded border border-amber-200 bg-white p-2 text-sm">
                  <div>
                    <span className="font-medium">{gap.title}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{gap.site}</span>
                  </div>
                  <a href={gap.url} target="_blank" rel="noreferrer"
                     className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                    <ExternalLink className="h-3 w-3" />
                    view
                  </a>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Fact type breakdown */}
      {s && (
        <div className="flex flex-wrap gap-2">
          {s.by_type.map((t) => (
            <button
              key={t.type}
              onClick={() => {
                setFilterType((prev) => (prev === t.type ? "" : t.type));
                setCurrentPage(1);
              }}
              className={`rounded-full border px-3 py-1 text-sm font-medium transition-all ${
                filterType === t.type
                  ? FACT_TYPE_COLORS[t.type] + " ring-2 ring-offset-1"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {t.type} ({t.count})
            </button>
          ))}
        </div>
      )}

      {/* Topic distribution */}
      {s && s.by_topic.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Knowledge by Topic</CardTitle>
            <p className="text-xs text-muted-foreground">Click a topic to filter the table below</p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {s.by_topic.map((t, i) => {
                const pct = Math.round((t.count / s.total_knowledge) * 100);
                return (
                  <button
                    key={t.topic}
                    onClick={() => handleTopicClick(t.topic)}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all hover:shadow-sm ${
                      filterTopic === t.topic
                        ? PILLAR_COLORS[i % PILLAR_COLORS.length] + " ring-2 ring-offset-1"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{t.topic}</span>
                      <span className="text-xs text-muted-foreground">{t.count} entries ({pct}%)</span>
                    </div>
                    {/* Mini bar */}
                    <div className="h-6 w-16 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full bg-sage-400"
                        style={{ width: `${Math.max(pct, 5)}%` }}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
            {filterTopic && (
              <button
                onClick={() => { setFilterTopic(""); setCurrentPage(1); }}
                className="mt-2 text-xs text-blue-600 hover:underline"
              >
                Clear topic filter
              </button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main content area */}
      {viewMode === "table" ? (
        <KnowledgeTable
          results={filteredResults}
          total={browse.data?.total ?? 0}
          page={currentPage}
          totalPages={browse.data?.total_pages ?? 1}
          isLoading={browse.isLoading}
          searchText={searchText}
          onSearchChange={setSearchText}
          filterSite={filterSite}
          onSiteChange={(s) => { setFilterSite(s); setCurrentPage(1); }}
          onPageChange={setCurrentPage}
        />
      ) : (
        <KnowledgeGraph />
      )}
    </div>
  );
}

// --- Table view ---

function KnowledgeTable({
  results,
  total,
  page,
  totalPages,
  isLoading,
  searchText,
  onSearchChange,
  filterSite,
  onSiteChange,
  onPageChange,
}: {
  results: KnowledgeEntry[];
  total: number;
  page: number;
  totalPages: number;
  isLoading: boolean;
  searchText: string;
  onSearchChange: (v: string) => void;
  filterSite: string;
  onSiteChange: (v: string) => void;
  onPageChange: (p: number) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            All Knowledge Entries ({total})
          </CardTitle>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Filter results..."
                value={searchText}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-48 pl-8"
              />
            </div>
            <select
              value={filterSite}
              onChange={(e) => onSiteChange(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">All sources</option>
              <option value="gitavalley">Gita Valley</option>
              <option value="iskcon">ISKCON</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : results.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No knowledge entries found. Try adjusting your filters or crawl websites first.
          </p>
        ) : (
          <div className="space-y-2">
            {results.map((entry) => (
              <div
                key={entry.id}
                className="rounded-lg border p-3 transition-colors hover:bg-gray-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="flex-1 text-sm leading-relaxed">{entry.content}</p>
                  <span
                    className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
                      FACT_TYPE_COLORS[entry.fact_type] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {entry.fact_type}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                  {entry.topic && (
                    <span className="rounded bg-sage-50 px-1.5 py-0.5 font-medium">
                      {entry.topic}
                    </span>
                  )}
                  {entry.site && (
                    <span className="flex items-center gap-1">
                      <Globe className="h-3 w-3" />
                      {entry.site === "gitavalley" ? "Gita Valley" : "ISKCON"}
                    </span>
                  )}
                  {entry.page_title && (
                    <span className="truncate">{entry.page_title}</span>
                  )}
                  {entry.page_url && (
                    <a
                      href={entry.page_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-0.5 text-blue-600 hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      source
                    </a>
                  )}
                  {entry.keywords.length > 0 && (
                    <span className="text-gray-400">
                      {entry.keywords.slice(0, 3).join(", ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => onPageChange(page + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --- Graph view ---

function KnowledgeGraph() {
  const graphRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ w: 800, h: 500 });
  const [ForceGraph, setForceGraph] = useState<React.ComponentType<Record<string, unknown>> | null>(null);
  const [selectedNode, setSelectedNode] = useState<Record<string, unknown> | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "graph"],
    queryFn: () => api.getKnowledgeGraph(),
  });

  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default);
    });
  }, []);

  useEffect(() => {
    if (graphRef.current) {
      setDimensions({ w: graphRef.current.clientWidth, h: 500 });
    }
  }, []);

  const SITE_COLORS: Record<string, string> = {
    gitavalley: "#60a5fa",
    iskcon: "#a78bfa",
  };

  if (isLoading || !ForceGraph) {
    return (
      <Card>
        <CardContent className="flex h-[540px] items-center justify-center">
          <p className="text-muted-foreground">Loading graph...</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Card>
        <CardContent className="flex h-[540px] items-center justify-center">
          <p className="text-muted-foreground">No knowledge data to visualize</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Knowledge Map</CardTitle>
          <div className="flex gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="h-3.5 w-3.5 rounded-full bg-sage-500" />
              Topics
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-blue-400" />
              Gita Valley pages
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-purple-400" />
              ISKCON pages
            </span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Topics are hubs, pages orbit around their dominant topic. Node size = fact count. Click to inspect.
        </p>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex">
          <div ref={graphRef} className="h-[500px] flex-1 overflow-hidden rounded-bl-lg border-t bg-gray-950">
            <ForceGraph
              graphData={data}
              nodeLabel={(node: Record<string, unknown>) => {
                const count = node.count as number;
                return `${node.label}${count ? ` — ${count} facts` : ""}`;
              }}
              nodeColor={(node: Record<string, unknown>) => {
                if (node.type === "topic") return "#4a7c59";
                return SITE_COLORS[(node.site as string)] ?? "#94a3b8";
              }}
              nodeVal={(node: Record<string, unknown>) => (node.size as number) ?? 3}
              nodeCanvasObject={(node: Record<string, unknown>, ctx: CanvasRenderingContext2D, globalScale: number) => {
                const x = node.x as number;
                const y = node.y as number;
                const size = (node.size as number) ?? 3;
                const isTopic = node.type === "topic";
                const color = isTopic ? "#4a7c59" : (SITE_COLORS[(node.site as string)] ?? "#94a3b8");

                // Draw node circle
                ctx.beginPath();
                ctx.arc(x, y, size, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();

                // Draw label for topics always, pages only when zoomed
                if (isTopic || globalScale > 1.5) {
                  const label = node.label as string;
                  const fontSize = isTopic ? 14 / globalScale : 10 / globalScale;
                  ctx.font = `${isTopic ? "bold " : ""}${fontSize}px sans-serif`;
                  ctx.textAlign = "center";
                  ctx.fillStyle = isTopic ? "#ffffff" : "#cbd5e1";
                  ctx.fillText(label, x, y + size + fontSize + 2);
                }
              }}
              linkColor={() => "rgba(255,255,255,0.08)"}
              linkWidth={0.5}
              backgroundColor="#030712"
              width={selectedNode ? dimensions.w - 280 : dimensions.w}
              height={500}
              onNodeClick={(node: Record<string, unknown>) => setSelectedNode(node)}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          </div>

          {/* Detail panel */}
          {selectedNode && (
            <div className="w-[280px] border-l border-t bg-gray-900 p-4 text-sm text-gray-200">
              <div className="flex items-center justify-between">
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                  selectedNode.type === "topic"
                    ? "bg-sage-800 text-sage-200"
                    : "bg-blue-900 text-blue-200"
                }`}>
                  {selectedNode.type as string}
                </span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-500 hover:text-gray-300"
                >
                  close
                </button>
              </div>
              <h3 className="mt-2 text-base font-semibold text-white">
                {String(selectedNode.label)}
              </h3>
              {selectedNode.count ? (
                <p className="mt-1 text-gray-400">
                  {Number(selectedNode.count)} knowledge entries
                </p>
              ) : null}
              {selectedNode.site ? (
                <p className="mt-1 text-gray-400">
                  Source: {String(selectedNode.site) === "gitavalley" ? "Gita Valley" : "ISKCON"}
                </p>
              ) : null}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
