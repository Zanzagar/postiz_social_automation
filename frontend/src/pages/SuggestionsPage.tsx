import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Suggestion, type ContentRow } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ContentEditor } from "@/components/content/ContentEditor";
import { Lightbulb } from "lucide-react";

function suggestionToContentRow(s: Suggestion): ContentRow {
  return {
    row_number: 0,
    date: s.suggested_date,
    content_pillar: s.suggested_pillar,
    raw_text: s.content_idea,
    media_url: null,
    platforms: { instagram: true, facebook: true, tiktok: true, threads: true, linkedin: true },
    status: "draft",
    captions: {},
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "suggestion",
    auto_publish_at: null,
  };
}

export function SuggestionsPage() {
  const queryClient = useQueryClient();
  const [selectedSuggestion, setSelectedSuggestion] = useState<ContentRow | null>(null);

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
        <Card
          key={i}
          className="cursor-pointer transition-colors hover:bg-muted/30"
          onClick={() => setSelectedSuggestion(suggestionToContentRow(s))}
        >
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

      {/* ContentEditor in create mode */}
      <ContentEditor
        contentRow={selectedSuggestion}
        mode="create"
        isOpen={!!selectedSuggestion}
        onClose={() => setSelectedSuggestion(null)}
        onSave={() => {
          queryClient.invalidateQueries({ queryKey: ["suggestions"] });
          queryClient.invalidateQueries({ queryKey: ["drafts"] });
          setSelectedSuggestion(null);
        }}
      />
    </div>
  );
}
