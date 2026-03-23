import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MediaItem, MediaTag } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DriveImportDialog } from "@/components/media/DriveImportDialog";
import {
  Image as ImageIcon,
  X,
  ChevronLeft,
  ChevronRight,
  Calendar,
  TrendingUp,
  FileImage,
  Trash2,
  HardDrive,
  RefreshCw,
  Loader2,
} from "lucide-react";

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// --- Media Card ---

function MediaCard({
  item,
  onClick,
}: {
  item: MediaItem;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="group relative cursor-pointer overflow-hidden rounded-lg border border-border bg-card transition-all hover:shadow-lg hover:border-sage-400"
    >
      <div className="aspect-square w-full overflow-hidden bg-muted">
        {item.thumbnail_path ? (
          <img
            src={`/media/thumbnails/${item.thumbnail_path.split("/").pop()}`}
            alt={item.filename}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <FileImage className="h-12 w-12 text-muted-foreground/30" />
          </div>
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-medium text-foreground line-clamp-1">
          {item.filename}
        </h3>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{formatBytes(item.file_size)}</span>
          {item.width && item.height && (
            <>
              <span>·</span>
              <span>
                {item.width}×{item.height}
              </span>
            </>
          )}
        </div>
        {item.pillar && (
          <Badge variant="outline" className="mt-2 text-xs">
            {item.pillar}
          </Badge>
        )}
      </div>
    </div>
  );
}

// --- Media Detail Dialog ---

function MediaDetailDialog({
  mediaId,
  open,
  onOpenChange,
}: {
  mediaId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [editingTags, setEditingTags] = useState(false);
  const [tagInput, setTagInput] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["media", "detail", mediaId],
    queryFn: () => api.getMediaDetail(mediaId!),
    enabled: !!mediaId && open,
  });

  const tagMutation = useMutation({
    mutationFn: ({
      add,
      remove,
    }: {
      add: string[];
      remove: string[];
    }) => api.updateMediaTags(mediaId!, add, remove),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media", "detail", mediaId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteMedia(mediaId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
      onOpenChange(false);
    },
  });

  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim();
    if (tag) {
      tagMutation.mutate({ add: [tag], remove: [] });
      setTagInput("");
    }
  }, [tagInput, tagMutation]);

  const handleRemoveTag = useCallback(
    (tag: string) => {
      tagMutation.mutate({ add: [], remove: [tag] });
    },
    [tagMutation],
  );

  const media = data?.media;
  const tags = data?.tags ?? [];
  const usage = data?.usage ?? [];
  const performance = data?.performance ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-muted-foreground">Loading...</div>
          </div>
        ) : media ? (
          <>
            <DialogHeader>
              <DialogTitle>{media.filename}</DialogTitle>
              <DialogDescription>
                {formatBytes(media.file_size)}
                {media.width && media.height && ` · ${media.width}×${media.height}`}
                {` · ${media.source}`}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6">
              {/* Image preview */}
              <div className="aspect-video w-full overflow-hidden rounded-lg border border-border bg-muted">
                {media.local_path ? (
                  <img
                    src={
                      media.local_path.startsWith("drive://")
                        ? `/api/media/drive/file/${media.local_path.replace("drive://", "")}`
                        : `/media/${media.local_path.split("/").pop()}`
                    }
                    alt={media.filename}
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <FileImage className="h-16 w-16 text-muted-foreground/30" />
                  </div>
                )}
              </div>

              {/* Tags */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Tags</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditingTags(!editingTags)}
                  >
                    {editingTags ? "Done" : "Edit"}
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {tags.map((t: MediaTag) => (
                    <Badge key={t.id} variant="secondary" className="gap-1">
                      {t.tag}
                      <span className="text-xs text-muted-foreground">
                        {Math.round(t.confidence * 100)}%
                      </span>
                      {editingTags && (
                        <button
                          onClick={() => handleRemoveTag(t.tag)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </Badge>
                  ))}
                  {tags.length === 0 && (
                    <span className="text-sm text-muted-foreground">No tags</span>
                  )}
                </div>
                {editingTags && (
                  <div className="flex gap-2">
                    <Input
                      placeholder="Add tag..."
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleAddTag();
                        }
                      }}
                    />
                    <Button onClick={handleAddTag} size="sm">
                      Add
                    </Button>
                  </div>
                )}
              </div>

              {/* Performance */}
              {performance.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold">Performance</h3>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {performance.map((p) => (
                      <div
                        key={p.id}
                        className="rounded-lg border border-border bg-card p-3"
                      >
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <TrendingUp className="h-4 w-4" />
                          <span className="text-xs">{p.platform}</span>
                        </div>
                        <p className="mt-1 text-lg font-bold">
                          {p.engagement_score.toFixed(2)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Usage history */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">
                  Usage History ({usage.length})
                </h3>
                {usage.length > 0 ? (
                  <div className="space-y-2">
                    {usage.map((u) => (
                      <div
                        key={u.content_row_id}
                        className="flex items-center justify-between rounded-lg border border-border bg-card p-3"
                      >
                        <div>
                          <span className="text-sm font-medium">
                            Content #{u.content_row_id}
                          </span>
                          {u.pillar && (
                            <Badge variant="outline" className="ml-2 text-xs">
                              {u.pillar}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge
                            variant={u.status === "published" ? "default" : "secondary"}
                            className="text-xs"
                          >
                            {u.status}
                          </Badge>
                          {u.date && (
                            <>
                              <Calendar className="h-3 w-3" />
                              {formatDate(u.date)}
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Not used in any content yet
                  </p>
                )}
              </div>

              {/* Metadata */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Details</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-muted-foreground">Source</div>
                  <div>{media.source}</div>
                  <div className="text-muted-foreground">Type</div>
                  <div>{media.mime_type}</div>
                  <div className="text-muted-foreground">Times Used</div>
                  <div>{media.usage_count}</div>
                  <div className="text-muted-foreground">Added</div>
                  <div>{formatDate(media.created_at)}</div>
                </div>
              </div>

              {/* Delete */}
              <div className="border-t pt-4">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (confirm("Delete this media permanently?")) {
                      deleteMutation.mutate();
                    }
                  }}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  {deleteMutation.isPending ? "Deleting..." : "Delete Media"}
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

// --- Main Page ---

export function MediaPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [source, setSource] = useState("all");
  const [pillar, setPillar] = useState("all");
  const [sort, setSort] = useState("date");
  const [selectedMediaId, setSelectedMediaId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [driveDialogOpen, setDriveDialogOpen] = useState(false);

  const syncMutation = useMutation({
    mutationFn: () => api.syncDrive(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
      alert(`Synced: ${data.imported} new, ${data.skipped} already imported`);
    },
    onError: (err) => {
      alert(`Sync failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    },
  });

  const pillars = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(true),
  });

  const media = useQuery({
    queryKey: ["media", page, source, pillar, sort],
    queryFn: () =>
      api.getMedia({
        page,
        per_page: 20,
        source: source !== "all" ? source : undefined,
        pillar: pillar !== "all" ? pillar : undefined,
        sort,
      }),
  });

  const data = media.data;
  const totalPages = data?.total_pages ?? 0;

  const handleMediaClick = (id: number) => {
    setSelectedMediaId(id);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Media Library</h1>
          <p className="text-sm text-muted-foreground">
            Browse and manage your media catalog
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Sync Drive
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => setDriveDialogOpen(true)}
          >
            <HardDrive className="h-4 w-4" />
            Browse Drive
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2">
          <Select
            value={source}
            onValueChange={(v) => {
              setSource(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="upload">Upload</SelectItem>
              <SelectItem value="import_url">Import URL</SelectItem>
              <SelectItem value="drive">Google Drive</SelectItem>
              <SelectItem value="social_import">Social Import</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={pillar}
            onValueChange={(v) => {
              setPillar(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Pillar" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Pillars</SelectItem>
              {(pillars.data ?? []).map((p) => (
                <SelectItem key={p.id} value={p.name}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="date">Newest First</SelectItem>
            <SelectItem value="engagement">Top Engagement</SelectItem>
            <SelectItem value="usage_count">Most Used</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results count */}
      {data && (
        <div className="text-sm text-muted-foreground">
          {data.total} {data.total === 1 ? "item" : "items"}
        </div>
      )}

      {/* Grid */}
      {media.isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="aspect-square animate-pulse rounded-lg bg-muted"
            />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {data.items.map((item) => (
            <MediaCard
              key={item.id}
              item={item}
              onClick={() => handleMediaClick(item.id)}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <ImageIcon className="h-12 w-12 text-muted-foreground/30" />
          <p className="mt-4 text-lg font-medium">No media found</p>
          <p className="text-sm text-muted-foreground">
            Upload images via the API or import from URLs
          </p>
        </div>
      )}

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Detail Dialog */}
      <MediaDetailDialog
        mediaId={selectedMediaId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />

      <DriveImportDialog
        open={driveDialogOpen}
        onOpenChange={setDriveDialogOpen}
      />
    </div>
  );
}
