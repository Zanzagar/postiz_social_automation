import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Loader2, PenLine, Save, Send, Sparkles, Undo2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Chip, PlatformDot } from "@/components/pasture";
import { api } from "@/lib/api";
import { platformBy } from "@/lib/platforms";
import { cn } from "@/lib/utils";
import type { CreateDraft } from "@/hooks/useLocalDraft";
import { appendHashtag, bareHashtag, captionHasHashtag, hashtagCount } from "./caption-utils";
import { IterMessage } from "./IterMessage";
import { PreviewRail } from "./PreviewRail";

const QUICK_CHIPS = ["Shorter", "Add a question", "More farm, less temple", "Stronger CTA"];

interface RefineStageProps {
  draft: CreateDraft;
  update: (patch: Partial<CreateDraft>) => void;
  onSaveDraft: () => void;
  onSend: () => void;
  isSaving: boolean;
  isSending: boolean;
}

/** Stage 3 — per-platform caption editing + Conversation with Claude. */
export function RefineStage({
  draft,
  update,
  onSaveDraft,
  onSend,
  isSaving,
  isSending,
}: RefineStageProps) {
  const platforms = draft.platforms.length > 0 ? draft.platforms : Object.keys(draft.captions);
  const [active, setActive] = useState(platforms[0] ?? "instagram");
  const [instruction, setInstruction] = useState("");
  const queryClient = useQueryClient();
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  /** Roving tabindex — Arrow/Home/End move focus AND select (mirrors PastureTabs). */
  function handleTabKeyDown(e: React.KeyboardEvent, index: number) {
    let next: number | null = null;
    if (e.key === "ArrowRight") next = (index + 1) % platforms.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + platforms.length) % platforms.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = platforms.length - 1;
    if (next === null) return;
    e.preventDefault();
    tabRefs.current[next]?.focus();
    setActive(platforms[next]);
  }

  const rowId = draft.rowId;
  const cap = draft.captions[active] ?? "";
  const meta = platformBy(active);
  const chars = cap.length;
  const pressure = meta.ideal > 0 ? Math.min(2, chars / meta.ideal) : 0;
  const tags = hashtagCount(cap);
  const tagsOver = meta.hashMax === 0 ? tags > 0 : tags > meta.hashMax;
  const tagsUnder = meta.hashMax > 0 && tags < meta.hashMin;
  const hashLimitLabel = meta.hashMax === 0 ? "none on Threads" : `${meta.hashMin}–${meta.hashMax}`;

  const { data: iterations = [] } = useQuery({
    queryKey: ["iterations", rowId],
    queryFn: () => api.getIterations(rowId!),
    enabled: rowId !== null,
  });

  const hashtagsEnabled = meta.hashMax > 0;
  const { data: hashtagSuggestions = [], isLoading: hashtagsLoading } = useQuery({
    queryKey: ["hashtags", active],
    queryFn: async () => {
      // Quiet degrade: some harnesses mock the api module without this
      // method, and a failed fetch should never surface an error banner.
      try {
        const res = await api.getHashtagSuggestions?.(active, 8);
        return res?.hashtags ?? [];
      } catch {
        return [];
      }
    },
    enabled: hashtagsEnabled,
  });

  function setCaption(platform: string, caption: string) {
    update({ captions: { ...draft.captions, [platform]: caption } });
  }

  const iterateMutation = useMutation({
    mutationFn: (vars: { platform: string; instruction: string }) =>
      api.iterate({
        content_row_id: rowId!,
        platform: vars.platform,
        instruction: vars.instruction,
        mode: "refine",
      }),
    onSuccess: (result, vars) => {
      setCaption(vars.platform, result.caption);
      setInstruction("");
      void queryClient.invalidateQueries({ queryKey: ["iterations", rowId] });
    },
  });

  const revertMutation = useMutation({
    mutationFn: (vars: { platform: string; iterationId?: number }) =>
      api.revertCaption(rowId!, vars.platform, vars.iterationId),
    onSuccess: (result, vars) => {
      setCaption(vars.platform, result.caption);
      void queryClient.invalidateQueries({ queryKey: ["iterations", rowId] });
    },
  });

  const visibleSuggestions = hashtagSuggestions.filter(
    (s) => !captionHasHashtag(cap, s.hashtag),
  );
  const atTagLimit = hashtagsEnabled && tags >= meta.hashMax;

  const platformIterations = iterations.filter((i) => i.platform === active);
  const missingAlt = !!draft.mediaUrl && !draft.altText.trim();
  const canIterate = rowId !== null;

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* LEFT: Editor + conversation */}
      <div
        className="flex-1 overflow-y-auto px-8 py-6"
        style={{ borderRight: "1px solid color-mix(in oklab, var(--ink) 12%, transparent)" }}
      >
        <div className="mx-auto max-w-2xl space-y-4">
          {/* Platform tabs */}
          <div
            role="tablist"
            aria-label="Platform"
            className="bg-card border-hair flex items-center gap-1 rounded-xl p-1"
          >
            {platforms.map((pid, i) => {
              const p = platformBy(pid);
              const on = pid === active;
              return (
                <button
                  key={pid}
                  ref={(el) => {
                    tabRefs.current[i] = el;
                  }}
                  role="tab"
                  aria-selected={on}
                  tabIndex={on ? 0 : -1}
                  type="button"
                  onClick={() => setActive(pid)}
                  onKeyDown={(e) => handleTabKeyDown(e, i)}
                  className={cn(
                    "fr t-ui flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg font-medium transition",
                    on
                      ? "shadow-card bg-sage-500 text-white"
                      : "ink hover:bg-sage-50 dark:hover:bg-sage-800/60",
                  )}
                >
                  <PlatformDot id={pid} size={10} />
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* Caption editor */}
          <div className="bg-card border-hair rounded-xl">
            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <div className="flex items-center gap-2">
                <div className="t-title-sm font-serif text-sage-800 capitalize dark:text-sage-100">
                  {meta.label} voice
                </div>
                <Chip tone="sage">v{platformIterations.length || 1} · current</Chip>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="iconSm"
                  aria-label="Copy caption"
                  onClick={() => {
                    void navigator.clipboard?.writeText(cap).catch(() => undefined);
                  }}
                >
                  <Copy size={13} strokeWidth={1.75} aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="iconSm"
                  aria-label="Undo last refinement"
                  disabled={!canIterate || revertMutation.isPending}
                  onClick={() => revertMutation.mutate({ platform: active })}
                >
                  <Undo2 size={13} strokeWidth={1.75} aria-hidden="true" />
                </Button>
              </div>
            </div>
            <div className="px-5 pt-1 pb-4">
              <Textarea
                rows={7}
                aria-label={`${meta.label} caption`}
                value={cap}
                onChange={(e) => setCaption(active, e.target.value)}
                className="t-body font-mono leading-relaxed"
              />
              <div className="t-caption mt-2 flex items-center justify-between">
                <span className="ink-muted">
                  <span
                    className={cn(
                      "font-medium",
                      pressure > 1.2
                        ? "text-red-600"
                        : pressure > 1
                          ? "text-terra-600"
                          : "text-sage-600 dark:text-sage-300",
                    )}
                  >
                    {chars}
                  </span>
                  {" / "}
                  {meta.ideal} ideal · {meta.max} max
                </span>
                <span
                  className={cn(
                    "font-medium",
                    tagsOver || tagsUnder
                      ? "text-terra-600"
                      : "text-sage-600 dark:text-sage-300",
                  )}
                >
                  {tags} hashtag{tags !== 1 ? "s" : ""}
                  <span className="ink-muted font-normal"> · {hashLimitLabel} ideal</span>
                  {tagsOver && <span className="text-red-600"> · too many</span>}
                </span>
              </div>

              {/* Suggested hashtags — from post history, quiet degrade on error/empty */}
              {hashtagsEnabled && (hashtagsLoading || visibleSuggestions.length > 0) && (
                <div className="mt-3">
                  <div className="t-micro ink-muted font-semibold tracking-wide uppercase">
                    Suggested tags
                  </div>
                  {hashtagsLoading ? (
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <span className="skeleton h-5 w-16 rounded-full" aria-hidden="true" />
                      <span className="skeleton h-5 w-20 rounded-full" aria-hidden="true" />
                    </div>
                  ) : (
                    <>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                        {visibleSuggestions.map((s) => (
                          <button
                            key={s.hashtag}
                            type="button"
                            aria-disabled={atTagLimit}
                            title={s.times_used > 0 ? `used ${s.times_used} times` : undefined}
                            onClick={() => {
                              if (atTagLimit) return;
                              setCaption(active, appendHashtag(cap, s.hashtag));
                            }}
                            className={cn(
                              "fr rounded-full",
                              atTagLimit && "cursor-not-allowed opacity-45",
                            )}
                          >
                            <Chip tone="sage">#{bareHashtag(s.hashtag)}</Chip>
                          </button>
                        ))}
                      </div>
                      <p className="t-micro ink-muted mt-1.5">From your post history</p>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Claude conversation (iteration history with diff) */}
          <div className="bg-card border-hair rounded-xl">
            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <div className="flex items-center gap-2">
                <Sparkles
                  size={15}
                  strokeWidth={1.75}
                  className="text-sage-600 dark:text-sage-300"
                  aria-hidden="true"
                />
                <span className="t-title-sm font-serif text-sage-800 dark:text-sage-100">
                  Conversation with Claude
                </span>
              </div>
              <span className="t-caption ink-muted">
                {platformIterations.filter((i) => i.old_caption).length} refinements
              </span>
            </div>
            <div className="space-y-3 px-5 pt-1 pb-4">
              {platformIterations.map((it) => (
                <IterMessage
                  key={it.id}
                  it={it}
                  onUse={(caption) => setCaption(active, caption)}
                  onRevert={(iterationId) =>
                    revertMutation.mutate({ platform: active, iterationId })
                  }
                />
              ))}

              {/* New iteration input */}
              <div className="rounded-xl border border-sage-100 bg-sage-50 p-3 dark:border-sage-800 dark:bg-sage-900/40">
                <div className="flex items-start gap-2.5">
                  <PenLine
                    size={14}
                    strokeWidth={1.75}
                    className="mt-1 shrink-0 text-sage-600 dark:text-sage-300"
                    aria-hidden="true"
                  />
                  <Textarea
                    rows={2}
                    aria-label="Refinement instruction"
                    placeholder="Tell Claude what to change… e.g. 'Shorter, lead with the feast' or 'Add a question at the end'"
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    className="t-ui bg-card border-sage-200 dark:border-sage-700"
                  />
                </div>
                <div className="mt-2 flex items-center justify-between pl-6">
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_CHIPS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        onClick={() => setInstruction(q)}
                        className="fr t-caption bg-card h-6 rounded-full border border-sage-200 px-2 text-sage-700 hover:bg-sage-100 dark:border-sage-700 dark:text-sage-300 dark:hover:bg-sage-800"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    disabled={!instruction.trim() || !canIterate || iterateMutation.isPending}
                    onClick={() =>
                      iterateMutation.mutate({ platform: active, instruction: instruction.trim() })
                    }
                  >
                    {iterateMutation.isPending ? (
                      <Loader2
                        size={12}
                        strokeWidth={1.75}
                        className="animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <Sparkles size={12} strokeWidth={1.75} aria-hidden="true" />
                    )}
                    Refine
                  </Button>
                </div>
                {iterateMutation.isError && (
                  <p className="t-caption mt-2 pl-6 text-terra-700 dark:text-terra-300" role="alert">
                    {iterateMutation.error instanceof Error
                      ? iterateMutation.error.message
                      : "Refinement failed"}
                  </p>
                )}
                {!canIterate && (
                  <p className="t-caption ink-muted mt-2 pl-6">
                    This draft isn't saved to a row yet — refinements are unavailable.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Footer actions */}
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="lg"
              className="flex-1"
              onClick={onSaveDraft}
              disabled={!canIterate || isSaving}
            >
              {isSaving ? (
                <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
              ) : (
                <Save size={14} strokeWidth={1.75} aria-hidden="true" />
              )}
              Save to Drafts
            </Button>
            {missingAlt && (
              <span role="status">
                <Chip tone="cream">NO ALT</Chip>
              </span>
            )}
            <Button
              size="lg"
              className="flex-1"
              onClick={onSend}
              disabled={missingAlt || isSending}
              aria-describedby={missingAlt ? "no-alt-message" : undefined}
            >
              {isSending ? (
                <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
              ) : (
                <Send size={14} strokeWidth={1.75} aria-hidden="true" />
              )}
              Send to Postiz
            </Button>
          </div>
          {missingAlt && (
            <p id="no-alt-message" className="t-caption text-terra-700 dark:text-terra-300">
              Add alt text to your image before publishing
            </p>
          )}
        </div>
      </div>

      {/* RIGHT: Live preview */}
      <PreviewRail platform={active} caption={cap} mediaUrl={draft.mediaUrl || null} />
    </div>
  );
}
