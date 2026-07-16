import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Loader2, Send, Sparkles, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { api, type MediaDetailResponse, type MediaUpdatePatch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PillarChip, SkeletonText, StatusPill, TextLink } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PlatformVersions } from "./PlatformVersions";
import {
  applyMediaPatch,
  errorDetail,
  formatBytes,
  formatMediaDate,
  fullMediaUrl,
  thumbnailUrl,
} from "./media-utils";

const SEASONS = [
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "fall", label: "Fall" },
  { value: "winter", label: "Winter" },
  { value: "any", label: "Any" },
];

interface MediaInspectorProps {
  mediaId: number;
  /** Rendered inside the small-screen GVSheet (tighter framing). */
  inSheet?: boolean;
  /** Called after a successful delete so the host can clear selection. */
  onDeleted?: () => void;
}

/**
 * Media detail inspector — shared by the desktop right-hand aside and the
 * below-`lg` GVSheet so both render paths show identical content.
 */
export function MediaInspector({ mediaId, inSheet = false, onDeleted }: MediaInspectorProps) {
  const { data, isError, refetch } = useQuery({
    queryKey: ["media", "detail", mediaId],
    queryFn: () => api.getMediaDetail(mediaId),
  });

  if (isError) {
    return (
      <div className={cn("space-y-2", inSheet ? "py-2" : "p-5")}>
        <p className="t-caption ink-muted">
          Couldn't load this item — it may have been deleted.
        </p>
        <TextLink className="t-caption" onClick={() => void refetch()}>
          Retry
        </TextLink>
      </div>
    );
  }

  if (!data) {
    return (
      <div
        role="status"
        aria-label="Loading media details"
        className={cn("space-y-4", inSheet ? "py-2" : "p-5")}
      >
        <div className="skeleton aspect-[4/5] w-full rounded-lg" />
        <SkeletonText lines={4} />
      </div>
    );
  }

  // Keyed by media id so local edit state resets when selection changes,
  // but survives background refetches of the same item.
  return <InspectorBody key={data.media.id} detail={data} inSheet={inSheet} onDeleted={onDeleted} />;
}

interface InspectorBodyProps {
  detail: MediaDetailResponse;
  inSheet: boolean;
  onDeleted?: () => void;
}

function InspectorBody({ detail, inSheet, onDeleted }: InspectorBodyProps) {
  const media = detail.media;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const detailKey = ["media", "detail", media.id] as const;

  const [altText, setAltText] = useState(media.alt_text ?? "");
  const [caption, setCaption] = useState(media.default_caption ?? "");
  const [tagInput, setTagInput] = useState("");
  const [suggestions, setSuggestions] = useState<Array<{ tag: string; confidence: number }>>([]);
  const [showUsage, setShowUsage] = useState(false);
  const [deleteArmed, setDeleteArmed] = useState(false);

  const isVideo = media.mime_type.startsWith("video/");

  const patchMutation = useMutation({
    mutationFn: (patch: MediaUpdatePatch) => api.updateMedia(media.id, patch),
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: detailKey });
      const prev = queryClient.getQueryData<MediaDetailResponse>(detailKey);
      queryClient.setQueryData<MediaDetailResponse>(detailKey, (d) =>
        d ? { ...d, media: applyMediaPatch(d.media, patch) } : d,
      );
      return { prev };
    },
    onError: (_err, _patch, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(detailKey, ctx.prev);
      toast.error("Couldn't save changes");
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["media"] }),
  });

  const tagsMutation = useMutation({
    mutationFn: ({ add, remove }: { add: string[]; remove: string[] }) =>
      api.updateMediaTags(media.id, add, remove),
    onMutate: async ({ add, remove }) => {
      await queryClient.cancelQueries({ queryKey: detailKey });
      const prev = queryClient.getQueryData<MediaDetailResponse>(detailKey);
      queryClient.setQueryData<MediaDetailResponse>(detailKey, (d) => {
        if (!d) return d;
        const kept = d.tags.filter((t) => !remove.includes(t.tag));
        const existing = new Set(kept.map((t) => t.tag));
        // Placeholder ids stay strictly below the cache minimum so two quick
        // optimistic adds never collide (real ids are positive).
        const nextPlaceholderId = Math.min(0, ...kept.map((t) => t.id)) - 1;
        const added = add
          .filter((t) => !existing.has(t))
          .map((tag, i) => ({
            id: nextPlaceholderId - i,
            tag,
            confidence: 1,
            source: "manual",
          }));
        return { ...d, tags: [...kept, ...added] };
      });
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(detailKey, ctx.prev);
      toast.error("Couldn't update tags");
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["media"] }),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateMediaMeta(media.id),
    onSuccess: (res) => {
      setAltText(res.alt_text);
      setSuggestions(res.suggested_tags);
      toast.success("Claude refreshed the alt-text and season");
      void queryClient.invalidateQueries({ queryKey: ["media"] });
    },
    onError: (err) => toast.error(errorDetail(err, "AI generation failed")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteMedia(media.id),
    onSuccess: () => {
      toast.success(`Deleted ${media.filename}`);
      void queryClient.invalidateQueries({
        queryKey: ["media"],
        // Skip the just-deleted detail query — refetching it would 404.
        predicate: (query) =>
          !(query.queryKey[1] === "detail" && query.queryKey[2] === media.id),
      });
      onDeleted?.();
    },
    onError: (err) => toast.error(errorDetail(err, "Couldn't delete this item")),
  });

  function saveAltText() {
    const next = altText.trim() === "" ? null : altText;
    if (next === (media.alt_text ?? null)) return;
    patchMutation.mutate({ alt_text: next });
  }

  function saveCaption() {
    const next = caption.trim() === "" ? null : caption;
    if (next === (media.default_caption ?? null)) return;
    patchMutation.mutate({ default_caption: next });
  }

  function handleAddTag() {
    const tag = tagInput.trim();
    if (!tag) return;
    setTagInput("");
    if (detail.tags.some((t) => t.tag.toLowerCase() === tag.toLowerCase())) return;
    tagsMutation.mutate({ add: [tag], remove: [] });
  }

  function handleSuggestion(tag: string) {
    setSuggestions((s) => s.filter((x) => x.tag !== tag));
    if (!detail.tags.some((t) => t.tag.toLowerCase() === tag.toLowerCase())) {
      tagsMutation.mutate({ add: [tag], remove: [] });
    }
  }

  function handleDeleteClick() {
    if (!deleteArmed) {
      setDeleteArmed(true);
      return;
    }
    deleteMutation.mutate();
  }

  const visibleSuggestions = suggestions.filter(
    (s) => !detail.tags.some((t) => t.tag.toLowerCase() === s.tag.toLowerCase()),
  );

  return (
    <div>
      {/* Preview */}
      <div
        className={cn(
          "bg-warm aspect-[4/5] w-full overflow-hidden",
          inSheet && "border-hair rounded-lg",
        )}
      >
        {isVideo ? (
          <video
            controls
            src={fullMediaUrl(media.local_path)}
            poster={thumbnailUrl(media.thumbnail_path) ?? undefined}
            className="h-full w-full object-cover"
            aria-label={media.filename}
          />
        ) : (
          <img
            src={fullMediaUrl(media.local_path)}
            alt={media.alt_text || media.filename}
            className="h-full w-full object-cover"
          />
        )}
      </div>

      <div className={cn("space-y-4", inSheet ? "py-5" : "p-5")}>
        {/* 1. Filename */}
        <div>
          <div className="t-micro font-medium tracking-wider text-sage-600 uppercase dark:text-sage-300">
            Filename
          </div>
          <div className="ink mt-1 font-mono text-[13px] break-all">{media.filename}</div>
        </div>

        {/* 2. Alt-text */}
        <div className="space-y-1.5">
          <Label htmlFor="media-alt-text" className="t-caption ink font-medium">
            Alt-text
          </Label>
          <Textarea
            id="media-alt-text"
            rows={3}
            value={altText}
            onChange={(e) => setAltText(e.target.value)}
            onBlur={saveAltText}
            className="fr t-body-sm"
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="t-micro ink-muted">
              Screen-reader friendly · {altText.length} chars
            </span>
            {!isVideo && (
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                aria-busy={generateMutation.isPending}
                className="fr t-caption flex items-center gap-1 rounded-sm font-medium text-sage-600 hover:text-sage-700 disabled:opacity-60 dark:text-sage-300 dark:hover:text-sage-200"
              >
                {generateMutation.isPending ? (
                  <Loader2 size={11} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Sparkles size={11} strokeWidth={1.75} aria-hidden="true" />
                )}
                Regenerate with Claude
              </button>
            )}
          </div>
        </div>

        {/* 3. Caption (default) */}
        <div className="space-y-1.5">
          <Label htmlFor="media-caption" className="t-caption ink font-medium">
            Caption (default)
          </Label>
          <Textarea
            id="media-caption"
            rows={2}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            onBlur={saveCaption}
            className="fr t-body-sm"
          />
        </div>

        {/* 4. Tags */}
        <div className="space-y-1.5">
          <div className="t-caption ink font-medium">Tags</div>
          <div className="flex flex-wrap items-center gap-1.5">
            {detail.tags.map((t) => (
              <span
                key={t.tag}
                className="t-caption inline-flex items-center gap-1 rounded-full border border-sage-100 bg-sage-50 px-2 py-0.5 font-medium text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-100"
              >
                {t.tag}
                <button
                  type="button"
                  aria-label={`Remove ${t.tag}`}
                  onClick={() => tagsMutation.mutate({ add: [], remove: [t.tag] })}
                  className="fr relative -mr-0.5 rounded-full p-0.5 before:absolute before:-inset-4 before:content-[''] hover:bg-black/5 dark:hover:bg-white/10"
                >
                  <X size={11} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </span>
            ))}
            <label htmlFor="media-add-tag" className="sr-only">
              Add tag
            </label>
            <input
              id="media-add-tag"
              placeholder="add…"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddTag();
                }
              }}
              className="fr t-caption ink w-16 min-w-0 rounded-full border border-transparent bg-transparent px-1.5 py-0.5 placeholder:text-muted-foreground focus:border-input"
            />
          </div>
          {visibleSuggestions.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="t-micro ink-muted">Claude suggests:</span>
              {visibleSuggestions.map((s) => (
                <button
                  key={s.tag}
                  type="button"
                  onClick={() => handleSuggestion(s.tag)}
                  className="fr t-caption inline-flex items-center rounded-full border border-cream-300 bg-cream-100 px-2 py-0.5 font-medium text-cream-ink dark:border-cream-400/40 dark:bg-cream-400/15"
                >
                  + {s.tag}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 5. Season + Used in */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="media-season" className="t-caption ink font-medium">
              Season
            </Label>
            <Select
              // Fully controlled from the cache ("" = placeholder) so the
              // optimistic-rollback in onError visually reverts a failed save.
              value={media.season ?? ""}
              onValueChange={(v) => {
                if (v !== media.season) patchMutation.mutate({ season: v });
              }}
            >
              <SelectTrigger id="media-season" size="sm" className="fr w-full">
                <SelectValue placeholder="Not set" />
              </SelectTrigger>
              <SelectContent>
                {SEASONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <div className="t-caption ink font-medium">Used in</div>
            <div className="t-body-sm ink flex h-7 items-center gap-1.5">
              {detail.usage.length === 0 ? (
                <span className="ink-muted">Not used yet</span>
              ) : (
                <>
                  <span>
                    {detail.usage.length} {detail.usage.length === 1 ? "post" : "posts"}
                  </span>
                  <TextLink className="t-caption" onClick={() => setShowUsage((v) => !v)}>
                    see
                  </TextLink>
                </>
              )}
            </div>
          </div>
        </div>
        {showUsage && detail.usage.length > 0 && (
          <div className="space-y-1.5">
            {detail.usage.map((u) => (
              <div
                key={u.content_row_id}
                className="bg-card border-hair flex items-center gap-2 rounded-lg px-2.5 py-1.5"
              >
                <span className="t-caption ink font-mono">#{u.content_row_id}</span>
                <span className="t-caption ink-muted flex-1">
                  {u.date ? formatMediaDate(u.date) : "—"}
                </span>
                <StatusPill status={u.status} size="xs" />
                {u.pillar && <PillarChip pillar={u.pillar} size="xs" />}
              </div>
            ))}
          </div>
        )}

        {/* 6. Platform versions */}
        <PlatformVersions media={media} />

        {/* 7. Metadata */}
        <div className="bg-warm border-hair rounded-lg p-3">
          <dl className="t-caption grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 font-mono">
            <dt className="ink-muted">Uploaded</dt>
            <dd className="ink text-right">{formatMediaDate(media.created_at)}</dd>
            <dt className="ink-muted">Dimensions</dt>
            <dd className="ink text-right">
              {media.width && media.height ? `${media.width} × ${media.height}` : "—"}
            </dd>
            <dt className="ink-muted">Size</dt>
            <dd className="ink text-right">{formatBytes(media.file_size)}</dd>
            <dt className="ink-muted">Source</dt>
            <dd className="ink text-right">{media.source}</dd>
          </dl>
        </div>

        {/* 8. Actions */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <Button
            size="sm"
            className="fr"
            onClick={() => navigate(`/create?media=${media.id}`)}
          >
            <Send size={12} strokeWidth={1.75} aria-hidden="true" />
            Use in a draft
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="fr text-terra-600 hover:text-terra-700 dark:text-terra-300 dark:hover:text-terra-200"
            onClick={handleDeleteClick}
            disabled={deleteMutation.isPending}
            aria-busy={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? (
              <Loader2 size={12} className="animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 size={12} strokeWidth={1.75} aria-hidden="true" />
            )}
            {deleteArmed ? "Really delete?" : "Delete"}
          </Button>
        </div>
      </div>
    </div>
  );
}
