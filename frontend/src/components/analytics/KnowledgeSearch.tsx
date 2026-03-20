import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search, BookOpen, Globe, FileText } from "lucide-react";

const FACT_TYPE_LABELS: Record<string, string> = {
  program: "Program",
  event: "Event",
  quote: "Quote",
  link: "Link",
  description: "Description",
};

const FACT_TYPE_COLORS: Record<string, string> = {
  program: "bg-blue-100 text-blue-700",
  event: "bg-purple-100 text-purple-700",
  quote: "bg-amber-100 text-amber-700",
  link: "bg-green-100 text-green-700",
  description: "bg-gray-100 text-gray-700",
};

const SITE_LABELS: Record<string, string> = {
  gitavalley: "Gita Valley",
  iskcon: "ISKCON",
};

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedPillar, setSelectedPillar] = useState<string>("");

  const pillars = useQuery({
    queryKey: ["pillars", "active"],
    queryFn: () => api.getPillars(true),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "search", debouncedQuery, selectedPillar],
    queryFn: () => api.searchKnowledge(debouncedQuery, selectedPillar || undefined),
    enabled: debouncedQuery.length >= 2 || selectedPillar.length > 0,
  });

  const handleChange = (value: string) => {
    setQuery(value);
    clearTimeout((window as unknown as Record<string, ReturnType<typeof setTimeout>>).__ksTimer);
    (window as unknown as Record<string, ReturnType<typeof setTimeout>>).__ksTimer = setTimeout(
      () => setDebouncedQuery(value),
      300,
    );
  };

  const results = data?.results ?? [];
  const hasQuery = debouncedQuery.length >= 2 || selectedPillar.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BookOpen className="h-4 w-4" />
          Knowledge Search
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Search + filter controls */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search facts, programs, events..."
              value={query}
              onChange={(e) => handleChange(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={selectedPillar}
            onChange={(e) => setSelectedPillar(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All pillars</option>
            {(pillars.data ?? []).map((p) => (
              <option key={p.id} value={p.name}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Help text when empty */}
        {!hasQuery && (
          <div className="rounded-lg border border-dashed p-3 text-center">
            <p className="text-sm text-muted-foreground">
              Search extracted knowledge from crawled websites.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Includes facts, programs, events, and quotes from Gita Valley and ISKCON websites.
            </p>
          </div>
        )}

        {isLoading && hasQuery && (
          <div className="h-20 animate-pulse rounded bg-muted" />
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {results.map((r) => (
              <div key={r.id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm leading-relaxed">{r.content}</p>
                  <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${FACT_TYPE_COLORS[r.fact_type] ?? "bg-gray-100 text-gray-700"}`}>
                    {FACT_TYPE_LABELS[r.fact_type] ?? r.fact_type}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                  {r.pillar && (
                    <span className="rounded bg-sage-50 px-1.5 py-0.5">{r.pillar}</span>
                  )}
                  {r.site && (
                    <span className="flex items-center gap-1">
                      <Globe className="h-3 w-3" />
                      {SITE_LABELS[r.site] ?? r.site}
                    </span>
                  )}
                  {r.page_title && (
                    <span className="flex items-center gap-1 truncate">
                      <FileText className="h-3 w-3" />
                      {r.page_title}
                    </span>
                  )}
                </div>
              </div>
            ))}
            <p className="pt-1 text-center text-xs text-muted-foreground">
              {data?.count} result{data?.count !== 1 ? "s" : ""} found
            </p>
          </div>
        )}

        {hasQuery && !isLoading && results.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No knowledge entries found. Try crawling websites first to populate the knowledge base.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
