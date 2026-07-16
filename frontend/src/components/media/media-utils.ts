import { ApiError, type MediaItem, type MediaUpdatePatch } from "@/lib/api";

/**
 * Browser URL for a catalog thumbnail. `thumbnail_path` already contains the
 * `media/` prefix (e.g. `media/thumbnails/thumb_x.jpg`) — never double-prefix.
 */
export function thumbnailUrl(thumbnailPath: string | null): string | null {
  return thumbnailPath ? `/${thumbnailPath}` : null;
}

/**
 * Full-resolution URL for a media item's `local_path`:
 * `drive://<id>` → `/api/media/drive/file/<id>`; `media/<file>` → `/media/<file>`.
 */
export function fullMediaUrl(localPath: string): string {
  if (localPath.startsWith("drive://")) {
    return `/api/media/drive/file/${localPath.slice("drive://".length)}`;
  }
  return `/${localPath}`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function formatMediaDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Apply a PATCH body onto a cached MediaItem, returning a new copy
 * (optimistic cache updates). Fields present with null clear the value —
 * mirroring the backend PATCH semantics.
 */
export function applyMediaPatch(media: MediaItem, patch: MediaUpdatePatch): MediaItem {
  const next: MediaItem = { ...media };
  if (patch.alt_text !== undefined) next.alt_text = patch.alt_text;
  if (patch.default_caption !== undefined) next.default_caption = patch.default_caption;
  if (patch.season !== undefined) next.season = patch.season;
  if (patch.pillar !== undefined) next.pillar = patch.pillar;
  return next;
}

/** Human-readable message from an API failure, with a calm fallback. */
export function errorDetail(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.detail || fallback;
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
