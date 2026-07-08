import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Suggestion, type ContentRow, type MediaItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ContentEditor } from "@/components/content/ContentEditor";
import {
  CalendarPlus,
  FileImage,
  Image as ImageIcon,
  Lightbulb,
} from "lucide-react";

function suggestionToContentRow(s: Suggestion): ContentRow {
  return {
    row_number: -1,
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
    require_review: false,
    held_at: null,
    alt_text: null,
  };
}

function SuggestionMediaThumbs({ pillar }: { pillar: string }) {
  const { data } = useQuery({
    queryKey: ["media", "browse", "pillar", pillar],
    queryFn: () => api.getMedia({ pillar, per_page: 2, sort: "engagement" }),
    staleTime: 60_000,
  });

  const items = data?.items ?? [];
  if (items.length === 0) return null;

  return (
    <div className="flex gap-1.5 mt-2">
      {items.map((m: MediaItem) => (
        <div
          key={m.id}
          className="h-10 w-10 rounded overflow-hidden bg-muted flex-shrink-0"
          title={m.filename}
        >
          {m.thumbnail_path ? (
            <img
              src={`/media/thumbnails/${m.thumbnail_path.split("/").pop()}`}
              alt={m.filename}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <FileImage className="h-4 w-4 text-muted-foreground/30" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
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
        <Button asChild variant="outline" className="mt-4 gap-2">
          <Link to="/calendar">
            <CalendarPlus className="h-4 w-4" />
            Plan Content Calendar
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sage-800">Content Suggestions</h1>
        <Button asChild variant="outline" size="sm" className="gap-2">
          <Link to="/calendar">
            <CalendarPlus className="h-4 w-4" />
            Plan Calendar
          </Link>
        </Button>
      </div>

      {suggestions.map((s) => (
        <Card
          key={`${s.suggested_date}-${s.content_idea.slice(0, 30)}`}
          className="cursor-pointer transition-colors hover:bg-muted/30"
          onClick={() => setSelectedSuggestion(suggestionToContentRow(s))}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">{s.content_idea}</CardTitle>
            <Badge variant="outline">{s.suggested_pillar}</Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">{s.rationale}</p>
            <div className="flex items-center justify-between">
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                <span>Date: {s.suggested_date}</span>
                {s.media_suggestion && (
                  <span className="flex items-center gap-1">
                    <ImageIcon className="h-3 w-3" />
                    {s.media_suggestion}
                  </span>
                )}
              </div>
              <SuggestionMediaThumbs pillar={s.suggested_pillar} />
            </div>
          </CardContent>
        </Card>
      ))}

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
