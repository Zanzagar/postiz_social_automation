import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Globe, Share2, Database, FileText, MessageSquare } from "lucide-react";

const SOURCE_ICONS: Record<string, typeof Globe> = {
  gitavalley: Globe,
  iskcon: Globe,
  facebook: MessageSquare,
  instagram: MessageSquare,
};

const SOURCE_LABELS: Record<string, string> = {
  gitavalley: "Gita Valley (WordPress)",
  iskcon: "ISKCON Gita Nagari (WordPress)",
  facebook: "Facebook Page Posts",
  instagram: "Instagram Posts",
};

export function KnowledgeStatus() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "status"],
    queryFn: () => api.getKnowledgeStatus(),
  });

  const progress = useQuery({
    queryKey: ["knowledge", "progress"],
    queryFn: () => api.getCrawlProgress(),
    refetchInterval: (query) => query.state.data?.running ? 2000 : false,
  });

  const crawlMutation = useMutation({
    mutationFn: () => api.triggerCrawl(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
  });

  const importMutation = useMutation({
    mutationFn: () => api.triggerSocialImport(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge", "status"] });
    },
  });

  const sources = data?.sources ?? [];
  const isRunning = progress.data?.running ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Database className="h-4 w-4" />
          Knowledge Base
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Source breakdown */}
        {isLoading ? (
          <div className="h-24 animate-pulse rounded bg-muted" />
        ) : sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No data collected yet. Click "Crawl Websites" to fetch content from Gita Valley and ISKCON websites,
            or "Import Social" to pull Facebook/Instagram post history.
          </p>
        ) : (
          <div className="space-y-2">
            {sources.map((source) => {
              const Icon = SOURCE_ICONS[source.name] ?? FileText;
              const label = SOURCE_LABELS[source.name] ?? source.name;
              const count = source.page_count ?? source.post_count ?? 0;
              const countLabel = source.type === "web" ? "pages" : "posts";
              const lastDate = source.last_crawled ?? source.last_imported;
              return (
                <div key={source.name} className="flex items-center justify-between rounded-lg border p-2.5">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{label}</p>
                      {lastDate && (
                        <p className="text-xs text-muted-foreground">
                          Last updated: {new Date(lastDate).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="rounded-full bg-sage-100 px-2.5 py-0.5 text-sm font-medium text-sage-700">
                    {count} {countLabel}
                  </span>
                </div>
              );
            })}
            <div className="flex items-center gap-2 pt-1 text-sm">
              <Database className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">
                {data?.knowledge_entries ?? 0} extracted knowledge entries
              </span>
            </div>
          </div>
        )}

        {/* Crawl progress bar */}
        {isRunning && progress.data && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-blue-800">
                Crawling {progress.data.source}...
              </span>
              <span className="text-blue-600">
                {progress.data.current}/{progress.data.total}
              </span>
            </div>
            <p className="mt-1 text-xs text-blue-600">{progress.data.phase}</p>
            {progress.data.total > 0 && (
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-blue-200">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all duration-500"
                  style={{ width: `${Math.round((progress.data.current / progress.data.total) * 100)}%` }}
                />
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1"
            onClick={() => crawlMutation.mutate()}
            disabled={crawlMutation.isPending || isRunning}
          >
            <Globe className="mr-1.5 h-3.5 w-3.5" />
            Crawl Websites
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1"
            onClick={() => importMutation.mutate()}
            disabled={importMutation.isPending || isRunning}
          >
            <Share2 className="mr-1.5 h-3.5 w-3.5" />
            Import Social
          </Button>
        </div>

        {/* Feedback messages */}
        {crawlMutation.isSuccess && !isRunning && (
          <p className="text-xs text-green-600">Crawl complete! Data has been updated.</p>
        )}
        {importMutation.isSuccess && (
          <p className="text-xs text-green-600">Social import triggered.</p>
        )}
        {(crawlMutation.isError || importMutation.isError) && (
          <p className="text-xs text-red-600">Something went wrong. Check the console for details.</p>
        )}
      </CardContent>
    </Card>
  );
}
