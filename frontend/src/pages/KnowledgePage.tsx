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
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="flex items-center gap-3 p-4">
                <AlertTriangle className="h-8 w-8 text-amber-500" />
                <div>
                  <p className="text-2xl font-bold">{s.coverage_gaps.length}</p>
                  <p className="text-xs text-amber-700">Coverage Gaps</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
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

      {/* Topic cards */}
      {s && s.by_topic.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {s.by_topic.map((t, i) => (
            <button
              key={t.topic}
              onClick={() => handleTopicClick(t.topic)}
              className={`rounded-xl border p-4 text-left transition-all hover:shadow-md ${
                filterTopic === t.topic
                  ? PILLAR_COLORS[i % PILLAR_COLORS.length] + " ring-2 ring-offset-1"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <p className="text-lg font-bold">{t.count}</p>
              <p className="text-sm font-medium">{t.topic}</p>
              <p className="text-xs text-muted-foreground">knowledge entries</p>
            </button>
          ))}
        </div>
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
  const [ForceGraph, setForceGraph] = useState<React.ComponentType<Record<string, unknown>> | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "graph"],
    queryFn: () => api.getKnowledgeGraph(),
  });

  // Dynamic import to avoid SSR issues
  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default);
    });
  }, []);

  const nodeColors: Record<string, string> = {
    topic: "#4a7c59",
    page: "#3b82f6",
    program: "#2563eb",
    event: "#7c3aed",
    quote: "#d97706",
    link: "#059669",
    description: "#6b7280",
  };

  if (isLoading || !ForceGraph) {
    return (
      <Card>
        <CardContent className="flex h-96 items-center justify-center">
          <p className="text-muted-foreground">Loading graph...</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Card>
        <CardContent className="flex h-96 items-center justify-center">
          <p className="text-muted-foreground">No knowledge data to visualize</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Knowledge Graph</CardTitle>
        <div className="flex flex-wrap gap-3 text-xs">
          {Object.entries(nodeColors).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
              {type}
            </span>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div ref={graphRef} className="h-[500px] overflow-hidden rounded-lg border bg-gray-950">
          <ForceGraph
            graphData={data}
            nodeLabel={(node: Record<string, unknown>) => node.label as string}
            nodeColor={(node: Record<string, unknown>) => nodeColors[(node.type as string)] ?? "#999"}
            nodeVal={(node: Record<string, unknown>) => (node.size as number) ?? 2}
            linkColor={() => "rgba(255,255,255,0.1)"}
            backgroundColor="#030712"
            width={graphRef.current?.clientWidth ?? 800}
            height={500}
          />
        </div>
      </CardContent>
    </Card>
  );
}
