import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Film,
  Image as ImageIcon,
  Link as LinkIcon,
  Loader2,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { api, type MediaBrowseParams, type MediaItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyState, GVSheet, PageHeader } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DriveImportDialog } from "@/components/media/DriveImportDialog";
import { MediaInspector } from "@/components/media/MediaInspector";
import { errorDetail, formatBytes, thumbnailUrl } from "@/components/media/media-utils";

const PER_PAGE = 30;
const MAX_FILE_BYTES = 100 * 1024 * 1024;
const ALLOWED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "video/mp4",
  "video/quicktime",
  "video/webm",
]);

const TYPE_FILTERS = [
  { id: "all", label: "All" },
  { id: "photos", label: "Photos" },
  { id: "videos", label: "Videos" },
  { id: "untagged", label: "Untagged" },
] as const;

type TypeFilterId = (typeof TYPE_FILTERS)[number]["id"];

interface UploadRow {
  key: number;
  name: string;
  kind: "IMG" | "MP4";
}

function validateFile(file: File): string | null {
  if (file.type === "image/gif") {
    return `"${file.name}" is a GIF — those aren't supported. Save it as an MP4 clip or a JPEG/PNG still instead.`;
  }
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return `"${file.name}" isn't a supported format — JPEG, PNG, WebP, MP4, MOV, or WebM.`;
  }
  if (file.size > MAX_FILE_BYTES) {
    return `"${file.name}" is over the 100 MB limit.`;
  }
  return null;
}

/** Mirrors Tailwind's `lg` breakpoint so only ONE inspector instance exists. */
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window === "undefined" || window.innerWidth >= 1024,
  );
  useEffect(() => {
    function onResize() {
      setIsDesktop(window.innerWidth >= 1024);
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return isDesktop;
}

function MediaTile({
  item,
  selected,
  onSelect,
}: {
  item: MediaItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const isVideo = item.mime_type.startsWith("video/");
  const thumb = thumbnailUrl(item.thumbnail_path);
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "fr group relative aspect-[4/5] overflow-hidden rounded-lg border-2 text-left transition",
        selected
          ? "border-sage-500 ring-2 ring-sage-500/30"
          : "border-transparent hover:border-sage-300",
      )}
    >
      {thumb ? (
        <img
          src={thumb}
          alt={item.alt_text || item.filename}
          loading="lazy"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <span className="bg-warm absolute inset-0 flex items-center justify-center">
          {isVideo ? (
            <Film size={22} strokeWidth={1.75} className="ink-muted" aria-hidden="true" />
          ) : (
            <ImageIcon size={22} strokeWidth={1.75} className="ink-muted" aria-hidden="true" />
          )}
          <span className="sr-only">{item.filename}</span>
        </span>
      )}
      {isVideo && (
        <span className="absolute top-1.5 left-1.5 rounded bg-black/60 px-1 py-0.5 text-[9px] font-medium tracking-wider text-white">
          REEL
        </span>
      )}
      {!item.alt_text && (
        <span
          role="status"
          className="absolute top-1.5 right-1.5 rounded bg-terra-500 px-1 py-0.5 text-[9px] font-medium tracking-wider text-white"
        >
          NO ALT
        </span>
      )}
      <span
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent px-1.5 pt-5 pb-1"
      >
        <span className="t-micro block truncate text-white">{item.filename}</span>
      </span>
    </button>
  );
}

export function MediaPage() {
  const queryClient = useQueryClient();
  const isDesktop = useIsDesktop();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [page, setPage] = useState(1);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilterId>("all");
  const [pillar, setPillar] = useState("all");
  const [source, setSource] = useState("all");
  const [sort, setSort] = useState("date");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [driveOpen, setDriveOpen] = useState(false);
  const [urlFormOpen, setUrlFormOpen] = useState(false);
  const [urlValue, setUrlValue] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [uploads, setUploads] = useState<UploadRow[]>([]);

  const keyRef = useRef(0);
  const queueRef = useRef<Array<{ key: number; file: File }>>([]);
  const drainingRef = useRef(false);

  // Debounce the search box into the server-backed `q` param (300ms).
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(qInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [qInput]);

  const pillarsQuery = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
    staleTime: 60_000,
  });

  const params = useMemo<MediaBrowseParams>(() => {
    const p: MediaBrowseParams = { page, per_page: PER_PAGE, sort };
    if (q) p.q = q;
    if (typeFilter === "photos") p.media_type = "image";
    if (typeFilter === "videos") p.media_type = "video";
    if (typeFilter === "untagged") p.untagged = true;
    if (pillar !== "all") p.pillar = pillar;
    if (source !== "all") p.source = source;
    return p;
  }, [page, q, typeFilter, pillar, source, sort]);

  const browse = useQuery({
    queryKey: ["media", params],
    queryFn: () => api.getMedia(params),
    placeholderData: keepPreviousData,
  });
  const data = browse.data;

  const filtersActive =
    q !== "" || typeFilter !== "all" || pillar !== "all" || source !== "all";

  function clearFilters() {
    setQInput("");
    setQ("");
    setTypeFilter("all");
    setPillar("all");
    setSource("all");
    setPage(1);
  }

  // --- Uploads: sequential queue (backend is synchronous + AI-analyzes each
  // file, up to ~2 min — never parallel-blast it) ---

  const drainQueue = useCallback(async () => {
    if (drainingRef.current) return;
    drainingRef.current = true;
    for (;;) {
      const next = queueRef.current.shift();
      if (!next) break;
      try {
        const res = await api.uploadMediaFile(next.file);
        toast.success(`Added ${res.filename}`);
        void queryClient.invalidateQueries({ queryKey: ["media"] });
        setSelectedId(res.id);
      } catch (err) {
        toast.error(errorDetail(err, `Couldn't upload ${next.file.name}`));
      } finally {
        setUploads((rows) => rows.filter((r) => r.key !== next.key));
      }
    }
    drainingRef.current = false;
  }, [queryClient]);

  const handleFiles = useCallback(
    (files: File[]) => {
      const accepted: Array<{ key: number; file: File }> = [];
      for (const file of files) {
        const problem = validateFile(file);
        if (problem) {
          toast.error(problem);
          continue;
        }
        keyRef.current += 1;
        accepted.push({ key: keyRef.current, file });
      }
      if (accepted.length === 0) return;
      setUploads((rows) => [
        ...rows,
        ...accepted.map(({ key, file }) => ({
          key,
          name: file.name,
          kind: (file.type.startsWith("video/") ? "MP4" : "IMG") as UploadRow["kind"],
        })),
      ]);
      queueRef.current.push(...accepted);
      void drainQueue();
    },
    [drainQueue],
  );

  // Paste-from-clipboard uploads work anywhere on the page.
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const files = e.clipboardData?.files;
      if (files && files.length > 0) handleFiles(Array.from(files));
    }
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [handleFiles]);

  const importUrlMutation = useMutation({
    mutationFn: (url: string) => api.importMediaUrl(url),
    onSuccess: (res) => {
      toast.success(`Added ${res.filename}`);
      void queryClient.invalidateQueries({ queryKey: ["media"] });
      setSelectedId(res.id);
      setUrlValue("");
      setUrlFormOpen(false);
    },
    onError: (err) => toast.error(errorDetail(err, "Couldn't import that URL")),
  });

  function handleUrlSubmit(e: React.FormEvent) {
    e.preventDefault();
    const url = urlValue.trim();
    if (!url || importUrlMutation.isPending) return;
    importUrlMutation.mutate(url);
  }

  function openPicker() {
    fileInputRef.current?.click();
  }

  function selectTile(id: number) {
    setSelectedId(id);
    if (!isDesktop) setSheetOpen(true);
  }

  const handleDeleted = useCallback(() => {
    setSelectedId(null);
    setSheetOpen(false);
  }, []);

  return (
    <div className="flex h-full min-h-0">
      <div className="flex min-w-0 flex-1 flex-col">
        <PageHeader
          greeting="The media library"
          title="Images, reels, and stills"
          subtitle="Upload, tag, caption — Claude reuses these across platforms."
          icon={ImageIcon}
          right={
            <Button size="sm" className="fr" onClick={openPicker}>
              <Upload size={12} strokeWidth={1.75} aria-hidden="true" />
              Upload
            </Button>
          }
        />

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-8">
          {/* Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              const files = e.dataTransfer?.files;
              if (files && files.length > 0) handleFiles(Array.from(files));
            }}
            className={cn(
              "flex flex-wrap items-center gap-3 rounded-xl border-2 border-dashed p-3 transition-colors sm:p-4",
              dragActive
                ? "border-sage-500 bg-sage-50 dark:bg-sage-800/40"
                : "border-sage-200 dark:border-sage-700",
            )}
          >
            <button
              type="button"
              onClick={openPicker}
              className="fr flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-sage-100 bg-sage-50 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-200">
                <Upload size={16} strokeWidth={1.75} aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="ink block text-[13px] font-bold">
                  Drop photos or videos here, or paste from clipboard
                </span>
                <span className="t-caption ink-muted block">
                  JPEG, PNG, WebP, or MP4 up to 100 MB · Claude will suggest alt-text,
                  tags, and season
                </span>
              </span>
            </button>
            <span className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="fr"
                aria-expanded={urlFormOpen}
                onClick={() => setUrlFormOpen((v) => !v)}
              >
                <LinkIcon size={12} strokeWidth={1.75} aria-hidden="true" />
                From URL
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="fr"
                onClick={() => setDriveOpen(true)}
              >
                From Drive
              </Button>
            </span>
          </div>

          {urlFormOpen && (
            <form
              onSubmit={handleUrlSubmit}
              className="bg-card border-hair flex items-center gap-2 rounded-lg p-2.5"
            >
              <Label htmlFor="media-import-url" className="sr-only">
                Media URL
              </Label>
              <Input
                id="media-import-url"
                type="url"
                placeholder="https://example.org/photo.jpg"
                value={urlValue}
                onChange={(e) => setUrlValue(e.target.value)}
                className="fr"
              />
              <Button
                type="submit"
                size="sm"
                className="fr"
                disabled={urlValue.trim() === "" || importUrlMutation.isPending}
                aria-busy={importUrlMutation.isPending}
              >
                {importUrlMutation.isPending && (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                )}
                Import
              </Button>
            </form>
          )}

          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:w-56">
              <Search
                size={13}
                strokeWidth={1.75}
                className="ink-muted pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2"
                aria-hidden="true"
              />
              <Input
                type="search"
                aria-label="Search media"
                placeholder={data ? `Search ${data.total} items` : "Search"}
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                className="fr pl-8"
              />
            </div>
            <span className="t-caption ink-muted font-medium">Filters:</span>
            {TYPE_FILTERS.map((f) => {
              const active = typeFilter === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => {
                    setTypeFilter(f.id);
                    setPage(1);
                  }}
                  aria-pressed={active}
                  className={cn(
                    "fr t-body-sm flex h-8 items-center rounded-full px-3 font-medium transition",
                    active
                      ? "bg-sage-500 text-white"
                      : "bg-card border-hair ink hover:bg-sage-50 dark:hover:bg-sage-800",
                  )}
                >
                  {f.label}
                </button>
              );
            })}
            <Select
              value={pillar}
              onValueChange={(v) => {
                setPillar(v);
                setPage(1);
              }}
            >
              <SelectTrigger size="sm" className="fr" aria-label="Filter by pillar">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All pillars</SelectItem>
                {(pillarsQuery.data ?? []).map((p) => (
                  <SelectItem key={p.id} value={p.name}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={source}
              onValueChange={(v) => {
                setSource(v);
                setPage(1);
              }}
            >
              <SelectTrigger size="sm" className="fr" aria-label="Filter by source">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                <SelectItem value="upload">Upload</SelectItem>
                <SelectItem value="import_url">From URL</SelectItem>
                <SelectItem value="drive">Google Drive</SelectItem>
                <SelectItem value="social_import">Social import</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={sort}
              onValueChange={(v) => {
                setSort(v);
                setPage(1);
              }}
            >
              <SelectTrigger size="sm" className="fr" aria-label="Sort media">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date">Newest first</SelectItem>
                <SelectItem value="engagement">Top engagement</SelectItem>
                <SelectItem value="usage_count">Most used</SelectItem>
              </SelectContent>
            </Select>
            {data && (
              <span className="t-caption ink-muted ml-auto">
                {data.total} {data.total === 1 ? "item" : "items"} ·{" "}
                {formatBytes(data.storage_used_bytes)} used
              </span>
            )}
          </div>

          {/* Upload-in-progress rows */}
          {uploads.length > 0 && (
            <div className="space-y-2">
              {uploads.map((u) => (
                <div
                  key={u.key}
                  className="bg-card border-hair flex items-center gap-3 rounded-lg p-2.5"
                >
                  <span className="bg-warm border-hair flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
                    <span className="t-micro ink-muted font-mono font-medium">
                      {u.kind}
                    </span>
                  </span>
                  <span className="ink min-w-0 flex-1 truncate text-[13px] font-medium">
                    {u.name}
                  </span>
                  <span
                    role="progressbar"
                    aria-label={`Uploading ${u.name}`}
                    className="hidden h-1.5 w-24 overflow-hidden rounded-full sm:block md:w-40"
                  >
                    <span className="skeleton block h-full w-full" />
                  </span>
                  <span className="ink-muted shrink-0 font-mono text-[11px]">
                    Uploading & analyzing…
                  </span>
                </div>
              ))}
              <div className="flex items-center gap-2 rounded-lg border border-sage-100 bg-sage-50 px-3 py-2 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-100">
                <Sparkles
                  size={13}
                  strokeWidth={1.75}
                  aria-hidden="true"
                  className="shrink-0"
                />
                <span className="t-caption">
                  Claude is generating alt-text, tags, and a season guess for your
                  upload.
                </span>
              </div>
            </div>
          )}

          {/* Grid */}
          {browse.isLoading ? (
            <div
              role="status"
              aria-label="Loading media"
              className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5"
            >
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="skeleton aspect-[4/5] rounded-lg" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            filtersActive ? (
              <EmptyState
                icon={ImageIcon}
                title="Nothing matches those filters"
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    className="fr"
                    onClick={clearFilters}
                  >
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={ImageIcon}
                title="No media yet"
                body="Drop a photo above or import from Drive to start the library."
                action={
                  <Button size="sm" className="fr" onClick={openPicker}>
                    <Upload size={12} strokeWidth={1.75} aria-hidden="true" />
                    Upload
                  </Button>
                }
              />
            )
          ) : (
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">
              {data.items.map((item) => (
                <MediaTile
                  key={item.id}
                  item={item}
                  selected={selectedId === item.id}
                  onSelect={() => selectTile(item.id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                className="fr"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={12} strokeWidth={1.75} aria-hidden="true" />
                Prev
              </Button>
              <span className="t-caption ink-muted">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="fr"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight size={12} strokeWidth={1.75} aria-hidden="true" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Inspector aside (≥ lg). Below lg the same content opens in a GVSheet. */}
      <aside
        aria-label="Media details"
        className="bg-warm hidden w-[380px] shrink-0 overflow-y-auto border-l lg:block"
      >
        {isDesktop && selectedId != null ? (
          <MediaInspector mediaId={selectedId} onDeleted={handleDeleted} />
        ) : (
          <EmptyState className="pt-24" title="Select an item to edit its details." />
        )}
      </aside>

      {!isDesktop && sheetOpen && selectedId != null && (
        <GVSheet title="Media details" width={420} onClose={() => setSheetOpen(false)}>
          <MediaInspector mediaId={selectedId} inSheet onDeleted={handleDeleted} />
        </GVSheet>
      )}

      <DriveImportDialog open={driveOpen} onOpenChange={setDriveOpen} />

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
        aria-label="Upload files"
        className="hidden"
        onChange={(e) => {
          const files = e.currentTarget.files;
          if (files && files.length > 0) handleFiles(Array.from(files));
          e.currentTarget.value = "";
        }}
      />
    </div>
  );
}
