import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MediaSuggestion } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronUp,
  FileImage,
  ImagePlus,
  Loader2,
  X,
} from "lucide-react";
import { useState } from "react";

interface SuggestedMediaPanelProps {
  contentRowId: number | undefined;
  attachedMediaIds: number[];
  onAttachChange: (ids: number[]) => void;
}

export function SuggestedMediaPanel({
  contentRowId,
  attachedMediaIds,
  onAttachChange,
}: SuggestedMediaPanelProps) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: ["media", "suggest", contentRowId],
    queryFn: () => api.suggestMedia(contentRowId!),
    enabled: !!contentRowId,
  });

  const attachMutation = useMutation({
    mutationFn: (mediaId: number) =>
      api.attachMedia(contentRowId!, mediaId),
    onSuccess: (result) => {
      onAttachChange(result.media_catalog_ids);
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  const detachMutation = useMutation({
    mutationFn: (mediaId: number) =>
      api.detachMedia(contentRowId!, mediaId),
    onSuccess: (result) => {
      onAttachChange(result.media_catalog_ids);
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  const suggestions = data?.suggestions ?? [];

  if (!contentRowId) return null;

  return (
    <div className="border rounded-lg bg-muted/30">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
      >
        <span className="flex items-center gap-2">
          <ImagePlus className="h-4 w-4" />
          Suggested Media
          {attachedMediaIds.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {attachedMediaIds.length} attached
            </Badge>
          )}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-3">
          {/* Attached media */}
          {attachedMediaIds.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Attached:</span>
              <div className="flex gap-1 flex-wrap">
                {attachedMediaIds.map((id) => (
                  <Badge key={id} variant="outline" className="gap-1">
                    Media #{id}
                    <button
                      onClick={() => detachMutation.mutate(id)}
                      className="hover:text-destructive"
                      disabled={detachMutation.isPending}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Suggestions */}
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : suggestions.length > 0 ? (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {suggestions.map((s: MediaSuggestion) => {
                const isAttached = attachedMediaIds.includes(s.media_id);
                return (
                  <div
                    key={s.media_id}
                    className={`relative flex-shrink-0 w-20 cursor-pointer group ${
                      isAttached
                        ? "ring-2 ring-sage-500 rounded-lg"
                        : ""
                    }`}
                    title={`${s.filename}\nScore: ${s.relevance_score}\n${s.match_reasons.join(", ")}`}
                  >
                    <div className="aspect-square rounded-lg overflow-hidden bg-muted">
                      {s.thumbnail_path ? (
                        <img
                          src={`/media/thumbnails/${s.thumbnail_path.split("/").pop()}`}
                          alt={s.filename}
                          className="h-full w-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center">
                          <FileImage className="h-6 w-6 text-muted-foreground/30" />
                        </div>
                      )}
                    </div>
                    <div className="mt-1 text-center">
                      {isAttached ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs w-full px-1"
                          onClick={() => detachMutation.mutate(s.media_id)}
                          disabled={detachMutation.isPending}
                        >
                          Detach
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 text-xs w-full px-1"
                          onClick={() => attachMutation.mutate(s.media_id)}
                          disabled={attachMutation.isPending}
                        >
                          Attach
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground py-2">
              No media suggestions for this content
            </p>
          )}
        </div>
      )}
    </div>
  );
}
