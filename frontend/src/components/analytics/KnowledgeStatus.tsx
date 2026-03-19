import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Globe, Share2 } from "lucide-react";

export function KnowledgeStatus() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["knowledge", "status"],
    queryFn: () => api.getKnowledgeStatus(),
  });

  const crawlMutation = useMutation({
    mutationFn: () => api.triggerCrawl(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["knowledge", "status"] }),
  });

  const importMutation = useMutation({
    mutationFn: () => api.triggerSocialImport(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["knowledge", "status"] }),
  });

  const sources = data?.sources ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Knowledge Base</CardTitle>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => crawlMutation.mutate()}
            disabled={crawlMutation.isPending}
          >
            <Globe className="mr-1 h-3 w-3" />
            Crawl
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => importMutation.mutate()}
            disabled={importMutation.isPending}
          >
            <Share2 className="mr-1 h-3 w-3" />
            Import
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-20 animate-pulse rounded bg-muted" />
        ) : sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">No data sources configured</p>
        ) : (
          <div className="space-y-2">
            {sources.map((source) => (
              <div key={source.name} className="flex items-center justify-between text-sm">
                <span className="font-medium">{source.name}</span>
                <span className="text-muted-foreground">
                  {source.page_count != null && `${source.page_count} pages`}
                  {source.post_count != null && `${source.post_count} posts`}
                </span>
              </div>
            ))}
            <div className="pt-1 text-xs text-muted-foreground">
              {data?.knowledge_entries ?? 0} knowledge entries total
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
