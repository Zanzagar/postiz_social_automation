import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { Calendar, Copy, Eye, Leaf, MoreHorizontal } from "lucide-react";
import { toast } from "sonner";

import type { ContentRow } from "@/lib/api";
import { PLATFORMS } from "@/lib/platforms";
import { pillarColor, type PillarLike } from "@/lib/pillars";
import {
  Chip,
  CountdownChip,
  PillarChip,
  PlatformDots,
  StatusPill,
} from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

import { draftTitle, remainingLabel } from "./draft-utils";

/** Re-render clock — ticks every `intervalMs` while `enabled`. */
function useNow(intervalMs: number, enabled: boolean): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (!enabled) return;
    const timer = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, enabled]);
  return now;
}

interface DraftRowProps {
  draft: ContentRow;
  /** Pillar object from GET /api/pillars when known (colors), else the name */
  pillar?: PillarLike | string | null;
  /** Batch-approve checkbox (pending_approval rows only) */
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: () => void;
  onOpen: () => void;
  onHold?: () => void;
  onResume?: () => void;
  /** Publish-now trigger — the button renders only for approved|draft rows. */
  onPublish?: () => void;
}

/**
 * Workbench row — pillar-gradient leaf tile, serif title, status pill,
 * italic raw-text quote, platform dots, pillar chip, scheduled date, and a
 * hover action rail. Rows with auto_publish_at surface a CountdownChip.
 */
export function DraftRow({
  draft,
  pillar,
  selectable = false,
  selected = false,
  onToggleSelect,
  onOpen,
  onHold,
  onResume,
  onPublish,
}: DraftRowProps) {
  const title = draftTitle(draft.raw_text);
  const publishable =
    onPublish !== undefined &&
    (draft.status === "approved" || draft.status === "draft");
  const needsAlt = !!draft.media_url && !(draft.alt_text ?? "").trim();
  const noAltId = `no-alt-${draft.row_number}`;
  const color = pillarColor(pillar ?? draft.content_pillar ?? "");
  const platformIds = PLATFORMS.map((p) => p.id).filter(
    (id) => draft.platforms[id],
  );
  const paused = draft.held_at != null;
  const publishAt = draft.auto_publish_at
    ? parseISO(draft.auto_publish_at)
    : null;
  const now = useNow(30_000, publishAt !== null && !paused);

  async function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(draft.raw_text);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Couldn't copy to clipboard");
    }
  }

  function handleRowKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    // Only activate for keys pressed on the row itself — inner buttons and
    // checkboxes handle their own keyboard events (which bubble up here).
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOpen();
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={title}
      onClick={onOpen}
      onKeyDown={handleRowKeyDown}
      className="fr group bg-card border-hair flex cursor-pointer items-start gap-4 rounded-2xl px-5 py-4 transition hover:border-sage-300 hover:shadow-sm dark:hover:border-sage-600"
    >
      {selectable && (
        <span
          onClick={(e) => e.stopPropagation()}
          className="flex h-10 items-center"
        >
          <Checkbox
            checked={selected}
            onCheckedChange={onToggleSelect}
            aria-label={`Select ${title}`}
            className="fr"
          />
        </span>
      )}

      <div
        className="h-10 w-10 shrink-0 rounded-lg"
        style={{ background: `linear-gradient(135deg, ${color}, ${color}88)` }}
      >
        <div className="flex h-full w-full items-center justify-center text-white">
          <Leaf size={18} strokeWidth={1.75} aria-hidden="true" />
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <h3 className="t-title-sm truncate font-serif font-medium text-sage-800 dark:text-sage-100">
            {title}
          </h3>
          <StatusPill status={draft.status} />
        </div>
        <p className="t-body-sm ink-muted truncate italic">
          "{draft.raw_text}"
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <PlatformDots ids={platformIds} size={12} />
          {(pillar || draft.content_pillar) && (
            <PillarChip
              pillar={pillar ?? draft.content_pillar ?? ""}
              size="xs"
            />
          )}
          <span className="t-micro ink-muted flex items-center gap-1 font-mono">
            <Calendar size={11} strokeWidth={1.75} aria-hidden="true" />
            {format(parseISO(draft.date), "MMM d")}
          </span>
          {publishAt && (
            <span onClick={(e) => e.stopPropagation()}>
              <CountdownChip
                label={`Releases ${format(publishAt, "h:mm a")}`}
                remaining={remainingLabel(publishAt, now)}
                paused={paused}
                onToggle={paused ? onResume : onHold}
              />
            </span>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100">
        <Button
          size="iconSm"
          variant="ghost"
          className="fr"
          aria-label={`Preview ${title}`}
          onClick={(e) => {
            e.stopPropagation();
            onOpen();
          }}
        >
          <Eye size={13} strokeWidth={1.75} aria-hidden="true" />
        </Button>
        <Button
          size="iconSm"
          variant="ghost"
          className="fr"
          aria-label={`Copy ${title} text`}
          onClick={handleCopy}
        >
          <Copy size={13} strokeWidth={1.75} aria-hidden="true" />
        </Button>
        <Button
          size="iconSm"
          variant="ghost"
          className="fr"
          aria-label="More actions"
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal size={13} strokeWidth={1.75} aria-hidden="true" />
        </Button>
        {publishable && (
          <>
            {needsAlt && (
              <>
                <span onClick={(e) => e.stopPropagation()} title="Add alt text before publishing">
                  <Chip tone="cream">NO ALT</Chip>
                </span>
                <span id={noAltId} className="sr-only">
                  Add alt text before publishing
                </span>
              </>
            )}
            <Button
              size="sm"
              variant="secondary"
              className="fr"
              aria-label={`Publish ${title} now`}
              disabled={needsAlt}
              aria-describedby={needsAlt ? noAltId : undefined}
              onClick={(e) => {
                e.stopPropagation();
                onPublish?.();
              }}
            >
              Publish now
            </Button>
          </>
        )}
        <Button
          size="sm"
          variant="default"
          className="fr"
          aria-label={`Open ${title}`}
          onClick={(e) => {
            e.stopPropagation();
            onOpen();
          }}
        >
          Open
        </Button>
      </div>
    </div>
  );
}
