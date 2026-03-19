import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "search", debouncedQuery],
    queryFn: () => api.searchKnowledge(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  const handleChange = (value: string) => {
    setQuery(value);
    // Simple debounce via timeout
    clearTimeout((window as unknown as Record<string, ReturnType<typeof setTimeout>>).__ksTimer);
    (window as unknown as Record<string, ReturnType<typeof setTimeout>>).__ksTimer = setTimeout(
      () => setDebouncedQuery(value),
      300,
    );
  };

  const results = data?.results ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Knowledge Search</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search facts, programs, events..."
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {isLoading && debouncedQuery && (
          <div className="h-20 animate-pulse rounded bg-muted" />
        )}

        {results.length > 0 && (
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {results.map((r) => (
              <div key={r.id} className="rounded-lg border p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm">{r.content}</p>
                  <span className="shrink-0 rounded bg-sage-100 px-2 py-0.5 text-xs text-sage-700">
                    {r.fact_type}
                  </span>
                </div>
                <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                  {r.pillar && <span>{r.pillar}</span>}
                  {r.site && <span>from {r.site}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {debouncedQuery.length >= 2 && !isLoading && results.length === 0 && (
          <p className="text-sm text-muted-foreground">No results found</p>
        )}
      </CardContent>
    </Card>
  );
}
