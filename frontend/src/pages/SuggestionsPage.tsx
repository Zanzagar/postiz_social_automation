import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Lightbulb } from "lucide-react";

export function SuggestionsPage() {
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.getSuggestions(),
  });

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Content Suggestions</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  if (!suggestions || suggestions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <Lightbulb className="mb-4 h-12 w-12 text-sage-400" />
        <h2 className="text-xl font-semibold text-sage-700">No suggestions</h2>
        <p className="mt-1 text-muted-foreground">
          AI suggestions will appear here as content gaps are detected.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <h1 className="text-2xl font-bold text-sage-800">Content Suggestions</h1>

      {suggestions.map((s, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">{s.content_idea}</CardTitle>
            <Badge variant="outline">{s.suggested_pillar}</Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">{s.rationale}</p>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>Date: {s.suggested_date}</span>
              <span>Media: {s.media_suggestion}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
