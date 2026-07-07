import { useEffect, useRef, useState } from "react";
import { Check, Loader2, RotateCcw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PlatformDot } from "@/components/pasture";
import {
  fetchGenerateStream,
  request,
  type GenerateRequest,
} from "@/lib/api";
import { platformBy } from "@/lib/platforms";
import { cn } from "@/lib/utils";
import { hashtagCount, toneNote } from "./caption-utils";

interface GenerateStageProps {
  generateRequest: GenerateRequest;
  pillar: string;
  onDone: (rowId: number | null, captions: Record<string, string>) => void;
}

/**
 * Stage 2 — live SSE generation via POST /api/generate.
 * Rows advance waiting → writing → done as platform_done events arrive.
 * On stream error, offers a retry that falls back to /api/generate-sync.
 */
export function GenerateStage({ generateRequest, pillar, onDone }: GenerateStageProps) {
  const [captions, setCaptions] = useState<Record<string, string>>({});
  const [complete, setComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const startedRef = useRef(false);
  const aliveRef = useRef(true);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;
  const requestRef = useRef(generateRequest);

  useEffect(() => {
    aliveRef.current = true;
    // StrictMode-safe run-once guard — never fire two generation streams.
    if (!startedRef.current) {
      startedRef.current = true;
      void runStream();
    }
    return () => {
      aliveRef.current = false;
    };
  }, []);

  async function runStream() {
    try {
      for await (const ev of fetchGenerateStream(requestRef.current)) {
        if (!aliveRef.current) return;
        if (ev.status === "platform_done") {
          setCaptions((c) => ({ ...c, [ev.platform]: ev.caption }));
        } else if (ev.status === "done") {
          setCaptions(ev.captions);
          setComplete(true);
          const { row_id, captions: finalCaptions } = ev;
          setTimeout(() => {
            if (aliveRef.current) onDoneRef.current(row_id, finalCaptions);
          }, 600);
          return;
        } else if (ev.status === "error") {
          setError(ev.message);
          return;
        }
      }
    } catch (err) {
      if (aliveRef.current) {
        setError(err instanceof Error ? err.message : "Generation failed");
      }
    }
  }

  async function retrySync() {
    setError(null);
    setIsRetrying(true);
    try {
      const result = await request<{
        captions: Record<string, string>;
        row_id?: number;
      }>("/api/generate-sync", {
        method: "POST",
        body: JSON.stringify(requestRef.current),
      });
      if (!aliveRef.current) return;
      setCaptions(result.captions);
      setComplete(true);
      onDoneRef.current(result.row_id ?? null, result.captions);
    } catch (err) {
      if (aliveRef.current) {
        setError(err instanceof Error ? err.message : "Generation failed");
      }
    } finally {
      if (aliveRef.current) setIsRetrying(false);
    }
  }

  const platforms = requestRef.current.platforms;
  const doneCount = platforms.filter((p) => captions[p] !== undefined).length;
  const progress = complete ? 100 : Math.round((doneCount / Math.max(platforms.length, 1)) * 100);
  const writingId = error || complete ? null : platforms.find((p) => captions[p] === undefined);

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-8 text-center">
        <div className="relative mb-5 inline-block">
          <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-sage-500">
            <Sparkles size={26} strokeWidth={1.75} className="text-white" aria-hidden="true" />
            {!error && !complete && (
              <div
                className="absolute inset-0 animate-ping rounded-full border-2 border-sage-400"
                aria-hidden="true"
              />
            )}
          </div>
        </div>
        <div className="t-label text-sage-600 dark:text-sage-300">
          {error ? "Generation hit a snag" : "Claude is writing"}
        </div>
        <h2 className="t-h2 mt-1 mb-1 text-sage-800 dark:text-sage-100">Shaping each voice…</h2>
        <p className="t-ui ink-muted">Usually 30–90 seconds. You'll refine each one next.</p>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-terra-200 bg-terra-50 px-4 py-3 dark:border-terra-600 dark:bg-terra-700/20"
        >
          <span className="t-body-sm text-terra-700 dark:text-terra-200">{error}</span>
          <Button variant="outline" size="sm" onClick={retrySync} disabled={isRetrying}>
            {isRetrying ? (
              <Loader2 size={12} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            ) : (
              <RotateCcw size={12} strokeWidth={1.75} aria-hidden="true" />
            )}
            Retry
          </Button>
        </div>
      )}

      <div className="space-y-2.5">
        {platforms.map((pid) => {
          const p = platformBy(pid);
          const caption = captions[pid];
          const done = caption !== undefined;
          const active = pid === writingId;
          return (
            <div
              key={pid}
              className={cn(
                "overflow-hidden rounded-xl border transition",
                done
                  ? "bg-card border-sage-200 dark:border-sage-700"
                  : active
                    ? "bg-card shadow-card border-sage-300 dark:border-sage-600"
                    : "bg-card border-hair opacity-70",
              )}
            >
              <div className="flex h-11 items-center gap-3 px-4">
                <PlatformDot id={pid} size={14} />
                <span className="t-body flex-1 font-medium">{p.label}</span>
                {done ? (
                  <span className="t-body-sm flex items-center gap-1.5 font-medium text-sage-700 dark:text-sage-200">
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-sage-500 text-white">
                      <Check size={9} strokeWidth={1.75} aria-hidden="true" />
                    </span>
                    {caption.length}ch ready
                  </span>
                ) : active ? (
                  <span className="t-body-sm flex items-center gap-1.5 text-sage-600 dark:text-sage-300">
                    <span
                      className="pulse-dot inline-block h-2 w-2 rounded-full bg-sage-500"
                      aria-hidden="true"
                    />
                    writing…
                  </span>
                ) : (
                  <span className="t-body-sm ink-muted">waiting</span>
                )}
              </div>
              {done && (
                <>
                  <div className="t-body-sm ink-muted line-clamp-2 border-t border-sage-100 px-4 pt-0.5 pb-1 font-mono leading-relaxed dark:border-sage-800">
                    {caption}
                  </div>
                  <div className="t-caption ink-muted flex items-center gap-3 px-4 pb-2.5">
                    <span>{caption.length} chars</span>
                    <span aria-hidden="true">·</span>
                    <span>{hashtagCount(caption)} hashtags</span>
                    <span aria-hidden="true">·</span>
                    <span>tone: {toneNote(pid)}</span>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      <div
        className="bg-warm mt-6 h-1 overflow-hidden rounded-full"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Generation progress"
      >
        <div className="h-full bg-sage-500 transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="t-caption ink-muted mt-2 text-center">
        Using context from <span className="font-medium">brand voice</span>
        {pillar && (
          <>
            {" "}
            · <span className="font-medium">{pillar} pillar</span>
          </>
        )}{" "}
        · <span className="font-medium">Gita Valley knowledge</span>
      </div>
    </div>
  );
}
