import { useState } from "react";
import { format } from "date-fns";
import { Diff, Sparkles } from "lucide-react";

import type { IterationRecord } from "@/lib/api";

interface IterMessageProps {
  it: IterationRecord;
  onUse: (caption: string) => void;
  onRevert: (iterationId: number) => void;
}

function iterTime(createdAt: string): string {
  const d = new Date(createdAt);
  return Number.isNaN(d.getTime()) ? "" : format(d, "MMM d · h:mm a");
}

function ClaudeAvatar() {
  return (
    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sage-500 text-white">
      <Sparkles size={13} strokeWidth={1.75} aria-hidden="true" />
    </div>
  );
}

/** One turn in the Conversation with Claude — instruction + refined output. */
export function IterMessage({ it, onUse, onRevert }: IterMessageProps) {
  const [showDiff, setShowDiff] = useState(false);

  if (!it.old_caption) {
    // Initial generation — just the output
    return (
      <div className="flex gap-3">
        <ClaudeAvatar />
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="t-body-sm font-medium text-sage-800 dark:text-sage-100">
              Claude · initial draft
            </span>
            <span className="t-caption ink-muted">{iterTime(it.created_at)}</span>
          </div>
          <div className="bg-warm border-hair t-body-sm ink rounded-lg p-2.5 leading-relaxed whitespace-pre-wrap">
            {it.new_caption}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* User instruction */}
      <div className="flex justify-end gap-3">
        <div className="max-w-[80%] rounded-lg border border-terra-200 bg-terra-50 px-3 py-2 dark:border-terra-600 dark:bg-terra-700/20">
          <div className="t-caption mb-0.5 font-medium text-terra-700 dark:text-terra-200">
            You · {iterTime(it.created_at)}
          </div>
          <div className="t-ui text-terra-800 italic dark:text-terra-100">
            "{it.refinement_instruction}"
          </div>
        </div>
      </div>
      {/* Claude response with diff toggle */}
      <div className="flex gap-3">
        <ClaudeAvatar />
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="t-body-sm font-medium text-sage-800 dark:text-sage-100">
              Claude · refined
            </span>
            <button
              type="button"
              onClick={() => setShowDiff(!showDiff)}
              className="fr t-caption ml-auto flex items-center gap-1 rounded text-sage-600 hover:text-sage-700 dark:text-sage-300"
            >
              <Diff size={11} strokeWidth={1.75} aria-hidden="true" />
              {showDiff ? "Hide" : "Show"} changes
            </button>
          </div>
          {showDiff ? (
            <div className="bg-warm border-hair t-body-sm space-y-1.5 rounded-lg p-2.5 leading-relaxed">
              <div className="flex gap-2">
                <span className="shrink-0 font-mono text-red-500" aria-hidden="true">
                  −
                </span>
                <span className="ink-muted line-through">{it.old_caption.slice(0, 120)}…</span>
              </div>
              <div className="flex gap-2">
                <span className="shrink-0 font-mono text-sage-500" aria-hidden="true">
                  +
                </span>
                <span className="whitespace-pre-wrap text-sage-800 dark:text-sage-100">
                  {it.new_caption}
                </span>
              </div>
            </div>
          ) : (
            <div className="t-body-sm rounded-lg border border-sage-200 bg-sage-50 p-2.5 leading-relaxed whitespace-pre-wrap text-sage-900 dark:border-sage-700 dark:bg-sage-800/60 dark:text-sage-100">
              {it.new_caption}
            </div>
          )}
          <div className="mt-1.5 flex items-center gap-2">
            <button
              type="button"
              onClick={() => onUse(it.new_caption)}
              className="fr t-caption rounded text-sage-600 hover:underline dark:text-sage-300"
            >
              Use this version
            </button>
            <span className="ink-muted" aria-hidden="true">
              ·
            </span>
            <button
              type="button"
              onClick={() => onRevert(it.id)}
              className="fr t-caption ink-muted rounded hover:text-sage-700 dark:hover:text-sage-300"
            >
              Revert
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
