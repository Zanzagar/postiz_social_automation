import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Bell, Check, Clock, ExternalLink } from "lucide-react";
import { toast } from "sonner";

import { GVSheet, PlatformDot } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { api, type PlatformPublishResult, type PublishNowResponse } from "@/lib/api";
import { platformBy } from "@/lib/platforms";

interface PublishModalProps {
  rowId: number;
  platforms: string[];
  title: string;
  onClose: () => void;
  onDone?: (response: PublishNowResponse) => void;
  /** Per-platform captions — only used for toast descriptions (real text). */
  captions?: Record<string, string | null>;
  /** Row date(-time) — rendered on "Scheduled · …" rows when present. */
  scheduledFor?: string | null;
}

/** First ~60 chars of a caption for the toast description. */
function excerpt(caption: string): string {
  const flat = caption.replace(/\s+/g, " ").trim();
  return flat.length > 60 ? `${flat.slice(0, 60).trimEnd()}…` : flat;
}

function fmtPostedAt(iso: string | null): string | null {
  if (!iso) return null;
  const d = parseISO(iso);
  if (Number.isNaN(d.getTime())) return null;
  return format(d, "h:mm a");
}

function fmtScheduledFor(value: string | null | undefined): string | null {
  if (!value) return null;
  const d = parseISO(value);
  if (Number.isNaN(d.getTime())) return null;
  return value.includes("T") ? format(d, "MMM d · h:mm a") : format(d, "MMM d");
}

/**
 * Publish-now modal — fires POST /api/content/{id}/publish-now on mount and
 * reports per-platform results (design publish-states, PubRow vocabulary).
 * Shows only real facts: posted time, real error text, real links — never
 * invented engagement numbers.
 */
export function PublishModal({
  rowId,
  platforms,
  title,
  onClose,
  onDone,
  captions,
  scheduledFor,
}: PublishModalProps) {
  const publishMutation = useMutation({
    mutationFn: () => api.publishNow(rowId),
    onSuccess: (res) => {
      const posted = res.results.filter((r) => r.status === "posted");
      const failed = res.results.filter((r) => r.status === "failed");
      for (const r of posted) {
        const label = platformBy(r.platform).label;
        const caption = captions?.[r.platform] ?? "";
        toast.success(`Posted to ${label}`, {
          description: caption ? excerpt(caption) : undefined,
          action: r.link
            ? {
                label: "View",
                onClick: () =>
                  window.open(r.link ?? "", "_blank", "noopener,noreferrer"),
              }
            : undefined,
        });
      }
      if (failed.length > 0) {
        const names = failed.map((r) => platformBy(r.platform).label).join(", ");
        toast.warning(
          `Published to ${posted.length} of ${res.results.length} — ${names} failed`,
        );
      }
      onDone?.(res);
    },
  });

  // Fire exactly once on mount (ref guards StrictMode's double effect).
  const firedRef = useRef(false);
  const { mutate } = publishMutation;
  useEffect(() => {
    if (firedRef.current) return;
    firedRef.current = true;
    mutate();
  }, [mutate]);

  const response = publishMutation.data ?? null;
  const requestError =
    publishMutation.error instanceof Error
      ? publishMutation.error.message
      : publishMutation.isError
        ? "Publishing failed"
        : null;

  const results = response?.results ?? null;
  const rowCount = results ? results.length : platforms.length;
  const postedCount = results
    ? results.filter((r) => r.status === "posted").length
    : 0;
  const postedTime = fmtPostedAt(response?.posted_at ?? null);
  const scheduledText = fmtScheduledFor(scheduledFor);

  return (
    <GVSheet
      title={`Publishing "${title}"`}
      width={480}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-between">
          <span className="t-caption ink-muted">
            {postedCount} of {rowCount} platforms published
          </span>
          <Button variant="ghost" size="sm" className="fr" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      {!response && !requestError && (
        <p className="t-caption ink-muted mb-3">
          Sending to {platforms.length} platform
          {platforms.length === 1 ? "" : "s"}.
        </p>
      )}

      {requestError && (
        <div
          role="alert"
          className="t-body-sm mb-3 rounded-lg border border-terra-200 bg-terra-50 px-3 py-2 text-terra-700 dark:border-terra-600 dark:bg-terra-700/20 dark:text-terra-200"
        >
          {requestError}
        </div>
      )}

      <div aria-live="polite" className="space-y-1.5">
        {results
          ? results.map((r) => (
              <PubRow
                key={r.platform}
                result={r}
                postedTime={postedTime}
                scheduledText={scheduledText}
              />
            ))
          : !requestError &&
            platforms.map((pid) => <PendingRow key={pid} platform={pid} />)}
      </div>
    </GVSheet>
  );
}

function RowShell({
  platform,
  alert,
  children,
}: {
  platform: string;
  alert?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      role={alert ? "alert" : undefined}
      className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-sage-50/40 dark:hover:bg-sage-800/40"
    >
      <PlatformDot id={platform} size={14} />
      <span className="t-ui ink w-24 shrink-0 font-medium">
        {platformBy(platform).label}
      </span>
      {children}
    </div>
  );
}

/** A platform we're still waiting on — spinner ring + "Sending…". */
function PendingRow({ platform }: { platform: string }) {
  return (
    <RowShell platform={platform}>
      <span className="t-caption ink-muted min-w-0 flex-1 truncate">
        Sending…
      </span>
      <span
        className="inline-block h-2.5 w-2.5 shrink-0 animate-spin rounded-full border-2 border-sage-500 border-t-transparent"
        aria-hidden="true"
      />
    </RowShell>
  );
}

/** One per-platform result row — PubRow vocabulary from the design mock. */
function PubRow({
  result,
  postedTime,
  scheduledText,
}: {
  result: PlatformPublishResult;
  postedTime: string | null;
  scheduledText: string | null;
}) {
  const label = platformBy(result.platform).label;

  if (result.status === "failed") {
    return (
      <RowShell platform={result.platform} alert>
        <span
          className="t-caption min-w-0 flex-1 truncate text-terra-700 dark:text-terra-300"
          title={result.error ?? undefined}
        >
          {result.error ?? "Failed"}
        </span>
        <span className="t-caption flex shrink-0 items-center gap-1 font-semibold text-terra-700 dark:text-terra-300">
          <Bell size={11} strokeWidth={1.75} aria-hidden="true" />
          Failed
        </span>
      </RowShell>
    );
  }

  if (result.status === "scheduled") {
    return (
      <RowShell platform={result.platform}>
        <span className="t-caption ink-muted min-w-0 flex-1 truncate">
          {scheduledText ? `Scheduled · ${scheduledText}` : "Scheduled"}
        </span>
        <span className="t-caption ink-muted flex shrink-0 items-center gap-1">
          <Clock size={11} strokeWidth={1.75} aria-hidden="true" />
          Scheduled
        </span>
      </RowShell>
    );
  }

  return (
    <RowShell platform={result.platform}>
      <span className="t-caption ink-muted min-w-0 flex-1 truncate">
        {postedTime ? `Posted · ${postedTime}` : "Posted"}
      </span>
      <span className="t-caption flex shrink-0 items-center gap-1 font-medium text-sage-700 dark:text-sage-300">
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-sage-500 text-white">
          <Check size={9} strokeWidth={2.5} aria-hidden="true" />
        </span>
        Posted
      </span>
      {result.link && (
        <a
          href={result.link}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`View on ${label}`}
          className="fr ink-muted flex h-7 w-7 shrink-0 items-center justify-center rounded-md hover:bg-sage-50 dark:hover:bg-sage-800"
        >
          <ExternalLink size={13} strokeWidth={1.75} aria-hidden="true" />
        </a>
      )}
    </RowShell>
  );
}
