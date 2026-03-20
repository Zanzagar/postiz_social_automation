import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TopPostsTable() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "top-posts"],
    queryFn: () => api.getTopPosts(5),
  });

  const posts = data?.posts ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Top Posts</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-32 animate-pulse rounded bg-muted" />
        ) : posts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No posts with analytics yet</p>
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <div key={`${post.id}-${post.platform}`} className="flex items-start justify-between gap-3 rounded-lg border p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{post.raw_text}</p>
                  <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                    <span>{post.platform}</span>
                    <span>{post.pillar}</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold">{post.engagement}</p>
                  <p className="text-xs text-muted-foreground">engagement</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
