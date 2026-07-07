import { Trash2 } from "lucide-react";

import { Chip, PlatformDot, TextLink } from "@/components/pasture";
import type { IterationRecord } from "@/lib/api";
import { platformBy } from "@/lib/platforms";
import { cn } from "@/lib/utils";

function fmtWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface EditorHistoryProps {
  iterations: IterationRecord[];
  /** Enabled platform ids (history is shown per selected platform) */
  platforms: string[];
  platform: string;
  onPlatformChange: (id: string) => void;
  onRestore: (iterationId: number) => void;
  onDelete: (iterationId: number) => void;
}

/**
 * Per-platform iteration history. The newest entry is the current caption
 * (sage row); older entries can be restored — restoring never deletes.
 */
export function EditorHistory({
  iterations,
  platforms,
  platform,
  onPlatformChange,
  onRestore,
  onDelete,
}: EditorHistoryProps) {
  const entries = iterations
    .filter((it) => it.platform === platform)
    .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);

  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5">
        <span className="t-label ink-muted">History — {platformBy(platform).label}</span>
        <span className="flex-1" />
        {platforms.length > 1 &&
          platforms.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => onPlatformChange(id)}
              aria-label={`Show ${platformBy(id).label} history`}
              aria-pressed={id === platform}
              className={cn(
                "fr rounded-full p-0.5 transition-opacity",
                id === platform ? "opacity-100" : "opacity-40 hover:opacity-70",
              )}
            >
              <PlatformDot id={id} size={11} />
            </button>
          ))}
      </div>
      {entries.length === 0 ? (
        <p className="t-caption ink-muted">
          No versions yet — the first iteration starts this platform's history.
        </p>
      ) : (
        <div className="space-y-1.5">
          {entries.map((it, i) => (
            <div
              key={it.id}
              className={cn(
                "flex h-11 items-center gap-3 rounded-lg border px-3",
                i === 0
                  ? "bg-sage-50 border-sage-200 dark:bg-sage-800 dark:border-sage-700"
                  : "bg-card border-hair",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 shrink-0 rounded-full",
                  i === 0 ? "bg-sage-500" : "bg-neutral-300 dark:bg-sage-700",
                )}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="t-body-sm ink truncate">
                  {it.refinement_instruction ?? "Original draft"}
                </div>
                <div className="t-micro ink-muted">{fmtWhen(it.created_at)}</div>
              </div>
              {i === 0 ? (
                <Chip tone="sage">current</Chip>
              ) : (
                <>
                  <TextLink className="t-caption shrink-0" onClick={() => onRestore(it.id)}>
                    Restore
                  </TextLink>
                  <button
                    type="button"
                    aria-label="Delete iteration"
                    onClick={() => onDelete(it.id)}
                    className="fr ink-muted rounded p-1 hover:text-red-700 dark:hover:text-red-400"
                  >
                    <Trash2 size={12} strokeWidth={1.75} aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
      <p className="t-micro ink-muted mt-2">
        Every version is kept. Restoring never deletes — it adds.
      </p>
    </div>
  );
}
