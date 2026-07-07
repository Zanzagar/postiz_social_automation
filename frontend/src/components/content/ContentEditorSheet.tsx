import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Sprout } from "lucide-react";
import { toast } from "sonner";

import {
  Chip,
  CountdownChip,
  GVSheet,
  PillarChip,
  PlatformDots,
  SkeletonText,
  StatusPill,
  Toggle,
} from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, request, type ContentRow } from "@/lib/api";
import { platformBy } from "@/lib/platforms";

import { EditorCaptionCard } from "./EditorCaptionCard";
import { EditorHistory } from "./EditorHistory";
import { EditorRepurpose } from "./EditorRepurpose";
import { EditorTemplateShell } from "./EditorTemplateShell";

export interface ContentEditorSheetProps {
  rowId: number | null;
  mode: "refine" | "repurpose";
  onClose: () => void;
  onSaved?: () => void;
}

// --- helpers ---

function deriveTitle(row: ContentRow): string {
  const first =
    row.raw_text
      .split("\n")
      .map((s) => s.trim())
      .find(Boolean) ?? "Untitled";
  return first.length > 64 ? `${first.slice(0, 61).trimEnd()}…` : first;
}

function enabledPlatforms(row: ContentRow): string[] {
  const flagged = Object.entries(row.platforms ?? {})
    .filter(([, on]) => on)
    .map(([id]) => id);
  if (flagged.length > 0) return flagged;
  return Object.keys(row.captions ?? {}).filter((k) => row.captions[k] != null);
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function fmtRemaining(iso: string, now: Date): string {
  const ms = new Date(iso).getTime() - now.getTime();
  if (ms <= 0) return "any moment";
  const mins = Math.round(ms / 60000);
  const h = Math.floor(mins / 60);
  return h > 0 ? `in ${h}h ${mins % 60}m` : `in ${mins}m`;
}

/** Re-render clock — ticks every `intervalMs` while `enabled` (same pattern as DraftRow). */
function useNow(intervalMs: number, enabled: boolean): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (!enabled) return;
    const timer = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, enabled]);
  return now;
}

function fmtScheduled(row: ContentRow): string {
  if (!row.date) return "Unscheduled";
  const hasTime = row.date.includes("T");
  const d = new Date(hasTime ? row.date : `${row.date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return row.date;
  const day = d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  return hasTime
    ? `${day} · ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
    : day;
}

/** Fire an autosave for a snapshotted (rowId, captions) payload. */
function fireDraftSave(id: number, snapshot: Record<string, string>) {
  void api.editDraft(id, snapshot).catch(() => {
    toast.error("Couldn't save the draft — your edits are still here.");
  });
}

/** Seed "carry forward" chips from the source post's DNA. */
function seedChips(row: ContentRow, platformIds: string[]): string[] {
  const chips: string[] = [];
  if (row.content_pillar) chips.push(row.content_pillar);
  const tags = new Set<string>();
  for (const caption of Object.values(row.captions ?? {})) {
    for (const tag of caption?.match(/#[\p{L}\d_]+/gu) ?? []) {
      if (tags.size < 3) tags.add(tag);
    }
  }
  chips.push(...tags);
  if (platformIds.length > 0) {
    chips.push(platformIds.map((id) => platformBy(id).label).join(" + "));
  }
  return chips;
}

/**
 * Unified ContentEditor — right-side sheet over Drafts/Calendar/Suggestions.
 * Refine mode edits an existing draft (per-platform captions, iterate,
 * history, release controls). Repurpose mode grows a NEW draft from a source
 * post — the original is never touched.
 */
export function ContentEditorSheet({ rowId, mode, onClose, onSaved }: ContentEditorSheetProps) {
  const qc = useQueryClient();
  const repurpose = mode === "repurpose";

  const { data: row } = useQuery({
    queryKey: ["content-row", rowId],
    queryFn: () => api.getContentRow(rowId as number),
    enabled: rowId != null,
  });
  const { data: iterations = [] } = useQuery({
    queryKey: ["iterations", rowId],
    queryFn: () => api.getIterations(rowId as number),
    enabled: rowId != null && !repurpose,
  });
  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const enabled = useMemo(() => (row ? enabledPlatforms(row) : []), [row]);

  // --- local state ---
  const [captions, setCaptions] = useState<Record<string, string>>({});
  const [historyPlatform, setHistoryPlatform] = useState("");
  const [carryChips, setCarryChips] = useState<string[]>([]);
  const [direction, setDirection] = useState("");
  const [altDraft, setAltDraft] = useState("");

  const captionsRef = useRef(captions);
  useEffect(() => {
    captionsRef.current = captions;
  }, [captions]);

  // Clock for the release countdown — ticks every 30s while the sheet shows
  // a scheduled auto-release, so "in Nm" doesn't freeze at open time.
  const now = useNow(30_000, rowId != null && row?.auto_publish_at != null);

  // Sync local state when a (new) row arrives — render-time state adjustment
  // per React's "adjusting state when props change" pattern.
  const [syncedRow, setSyncedRow] = useState<number | null>(null);
  if (rowId === null && syncedRow !== null) {
    // Sheet closed — reset tracking so reopening re-syncs.
    setSyncedRow(null);
  } else if (row && row.row_number !== syncedRow) {
    setSyncedRow(row.row_number);
    const next: Record<string, string> = {};
    for (const [k, v] of Object.entries(row.captions ?? {})) {
      if (v != null) next[k] = v;
    }
    setCaptions(next);
    const ids = enabledPlatforms(row);
    setHistoryPlatform(ids[0] ?? "");
    setCarryChips(seedChips(row, ids));
    setDirection("");
    setAltDraft("");
  }

  // Debounced caption autosave.
  //
  // The sheet is rendered persistently (no key) by its parent pages, so refs
  // survive row switches. To guarantee a pending save can never write another
  // row's captions, the (rowId, captions) payload is snapshotted in the
  // closure AT SCHEDULE TIME — the timer never reads live refs. When the row
  // changes (or the sheet closes/unmounts), the pending save is cancelled and
  // FLUSHED immediately so the last keystrokes on the previous row persist.
  const pendingSave = useRef<{
    id: number;
    captions: Record<string, string>;
    timer: ReturnType<typeof setTimeout>;
  } | null>(null);

  const flushPendingSave = useCallback(() => {
    const pending = pendingSave.current;
    if (!pending) return;
    clearTimeout(pending.timer);
    pendingSave.current = null;
    fireDraftSave(pending.id, pending.captions);
  }, []);

  // On row switch or close/unmount, flush the previous row's pending save.
  useEffect(() => {
    return () => flushPendingSave();
  }, [rowId, flushPendingSave]);

  function handleCaptionChange(platform: string, value: string) {
    if (rowId == null) return;
    // Synchronous snapshot so rapid keystrokes accumulate before re-render.
    const snapshot = { ...captionsRef.current, [platform]: value };
    captionsRef.current = snapshot;
    setCaptions(snapshot);
    if (pendingSave.current) clearTimeout(pendingSave.current.timer);
    const id = rowId;
    const timer = setTimeout(() => {
      pendingSave.current = null;
      fireDraftSave(id, snapshot);
    }, 900);
    pendingSave.current = { id, captions: snapshot, timer };
  }

  // --- mutations ---

  const iterateMutation = useMutation({
    mutationFn: (vars: { platform: string; instruction: string }) =>
      api.iterate({
        content_row_id: rowId as number,
        platform: vars.platform,
        instruction: vars.instruction,
        mode: "refine",
      }),
    onSuccess: (res, vars) => {
      setCaptions((prev) => ({ ...prev, [vars.platform]: res.caption }));
      setHistoryPlatform(vars.platform);
      void qc.invalidateQueries({ queryKey: ["iterations", rowId] });
      void qc.invalidateQueries({ queryKey: ["content-row", rowId] });
    },
    onError: () => toast.error("Iteration failed — try again."),
  });

  const revertMutation = useMutation({
    mutationFn: (vars: { platform: string; iterationId: number }) =>
      api.revertCaption(rowId as number, vars.platform, vars.iterationId),
    onSuccess: (res, vars) => {
      setCaptions((prev) => ({ ...prev, [vars.platform]: res.caption }));
      void qc.invalidateQueries({ queryKey: ["iterations", rowId] });
      void qc.invalidateQueries({ queryKey: ["content-row", rowId] });
    },
    onError: () => toast.error("Restore failed — try again."),
  });

  const deleteIterationMutation = useMutation({
    mutationFn: (iterationId: number) => api.deleteIteration(iterationId),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["iterations", rowId] }),
    onError: () => toast.error("Couldn't delete that version."),
  });

  const reviewMutation = useMutation({
    mutationFn: (value: boolean) => api.setRequireReview(rowId as number, value),
    onMutate: async (value) => {
      await qc.cancelQueries({ queryKey: ["content-row", rowId] });
      const prev = qc.getQueryData<ContentRow>(["content-row", rowId]);
      if (prev) {
        qc.setQueryData<ContentRow>(["content-row", rowId], {
          ...prev,
          require_review: value,
          // Turning review ON clears the countdown server-side
          auto_publish_at: value ? null : prev.auto_publish_at,
        });
      }
      return { prev };
    },
    onError: (_err, _value, ctx) => {
      if (ctx?.prev) qc.setQueryData(["content-row", rowId], ctx.prev);
      toast.error("Couldn't update review setting.");
    },
    onSuccess: (updated) => qc.setQueryData(["content-row", rowId], updated),
  });

  const holdMutation = useMutation({
    mutationFn: (paused: boolean) =>
      paused ? api.resumeContent(rowId as number) : api.holdContent(rowId as number),
    onSuccess: (updated) => qc.setQueryData(["content-row", rowId], updated),
    onError: () => toast.error("Couldn't update the release."),
  });

  const altMutation = useMutation({
    mutationFn: (text: string) => api.setAltText(rowId as number, text),
    onSuccess: (updated) => {
      qc.setQueryData(["content-row", rowId], updated);
      toast.success("Alt text saved.");
    },
    onError: () => toast.error("Couldn't save alt text."),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.approveDraft(rowId as number),
    onSuccess: () => {
      toast.success("Approved — scheduled for release.");
      onSaved?.();
      onClose();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Approve failed"),
  });

  const saveMutation = useMutation({
    mutationFn: () => api.editDraft(rowId as number, captionsRef.current),
    onSuccess: () => {
      toast.success("Draft saved.");
      onSaved?.();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Save failed"),
  });

  // Repurpose: create a NEW draft from the source post's DNA. The original
  // row is never written to.
  const generateMutation = useMutation({
    mutationFn: () => {
      const r = row as ContentRow;
      const parts = [r.raw_text];
      if (carryChips.length > 0) parts.push(`Carry forward: ${carryChips.join(", ")}`);
      if (direction.trim()) parts.push(`New direction: ${direction.trim()}`);
      return request<{ captions: Record<string, string>; row_id?: number }>(
        "/api/generate-sync?persist=true",
        {
          method: "POST",
          body: JSON.stringify({
            raw_text: parts.join("\n\n"),
            platforms: enabled,
            scheduled_date:
              r.date?.split("T")[0] ?? new Date().toISOString().split("T")[0],
            content_pillar: r.content_pillar,
          }),
        },
      );
    },
    onSuccess: () => {
      toast.success("New draft created — the original post is untouched.");
      onSaved?.();
      onClose();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Generation failed"),
  });

  // Template shells: fill variables, then use as-is or generate via Claude
  const shellMutation = useMutation({
    mutationFn: async (vars: { finalText: string; generate: boolean }) => {
      const r = row as ContentRow;
      let caps: Record<string, string>;
      if (vars.generate) {
        const res = await request<{ captions: Record<string, string> }>(
          "/api/generate-sync?persist=false",
          {
            method: "POST",
            body: JSON.stringify({
              raw_text: vars.finalText,
              platforms: enabled,
              scheduled_date:
                r.date?.split("T")[0] ?? new Date().toISOString().split("T")[0],
              content_pillar: r.content_pillar,
            }),
          },
        );
        caps = res.captions;
      } else {
        caps = Object.fromEntries(enabled.map((p) => [p, vars.finalText]));
      }
      return api.editDraft(r.row_number, caps, r.platforms);
    },
    onSuccess: (updated) => {
      qc.setQueryData(["content-row", rowId], updated);
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(updated.captions ?? {})) {
        if (v != null) next[k] = v;
      }
      setCaptions(next);
      toast.success("Captions ready — refine each platform below.");
      onSaved?.();
      void qc.invalidateQueries({ queryKey: ["iterations", rowId] });
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Generation failed"),
  });

  // --- derived ---

  const templateVars = useMemo(() => {
    if (!row) return [];
    const matches = row.raw_text.match(/\{\{(\w+)\}\}/g);
    return matches ? [...new Set(matches.map((m) => m.slice(2, -2)))] : [];
  }, [row]);
  const isTemplateShell =
    !repurpose &&
    row?.source === "template" &&
    templateVars.length > 0 &&
    Object.values(row.captions ?? {}).every((v) => v == null || v === "");

  const noAlt = !!row && !!row.media_url && !(row.alt_text ?? "").trim();
  const pillarObj = pillars.find((p) => p.name === row?.content_pillar);

  if (rowId === null) return null;

  const title = row ? deriveTitle(row) : "Loading…";

  // --- footers ---

  const refineFooter = row && (
    <div className="flex items-center gap-2.5">
      <Button
        onClick={() => approveMutation.mutate()}
        disabled={noAlt || approveMutation.isPending || isTemplateShell}
        aria-describedby={noAlt ? "alt-blocker-note" : undefined}
      >
        <Check size={14} strokeWidth={1.75} aria-hidden="true" />
        Approve &amp; schedule
      </Button>
      <Button
        variant="ghost"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending || isTemplateShell}
      >
        Save draft
      </Button>
      <span className="flex-1" />
      <span className="t-micro ink-muted font-mono">{fmtScheduled(row)}</span>
    </div>
  );

  const repurposeFooter = row && (
    <div className="flex items-center gap-2.5">
      <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
        <Sprout size={14} strokeWidth={1.75} aria-hidden="true" />
        {generateMutation.isPending ? "Generating…" : "Generate captions"}
      </Button>
      <Button variant="ghost" onClick={onClose}>
        Cancel
      </Button>
      <span className="flex-1" />
      <span className="t-micro ink-muted">
        Creates a new draft — the original post is untouched.
      </span>
    </div>
  );

  return (
    <GVSheet
      width={580}
      title={title}
      badge={<Chip tone={repurpose ? "cream" : "terra"}>{repurpose ? "Repurpose" : "Refine"}</Chip>}
      onClose={onClose}
      footer={repurpose ? repurposeFooter : refineFooter}
    >
      {!row ? (
        <SkeletonText lines={6} />
      ) : repurpose ? (
        <EditorRepurpose
          row={row}
          title={title}
          platforms={enabled}
          chips={carryChips}
          onRemoveChip={(chip) => setCarryChips((prev) => prev.filter((c) => c !== chip))}
          direction={direction}
          onDirectionChange={setDirection}
        />
      ) : (
        <div className="space-y-5">
          {/* Meta chip row */}
          <div className="flex flex-wrap items-center gap-2">
            {row.content_pillar && <PillarChip pillar={pillarObj ?? row.content_pillar} />}
            <Chip leading={<PlatformDots ids={enabled} size={12} />}>
              {enabled.length} platform{enabled.length === 1 ? "" : "s"}
            </Chip>
            <StatusPill status={row.status} />
            {noAlt && (
              <span role="status">
                <Chip tone="cream">NO-ALT</Chip>
              </span>
            )}
            {row.auto_publish_at && (
              <CountdownChip
                label={`Releases ${fmtTime(row.auto_publish_at)}`}
                remaining={fmtRemaining(row.auto_publish_at, now)}
                paused={row.held_at != null}
                onToggle={() => holdMutation.mutate(row.held_at != null)}
              />
            )}
          </div>

          {isTemplateShell ? (
            <EditorTemplateShell
              row={row}
              templateVars={templateVars}
              busy={shellMutation.isPending}
              onUseAsIs={(finalText) => shellMutation.mutate({ finalText, generate: false })}
              onGenerate={(finalText) => shellMutation.mutate({ finalText, generate: true })}
            />
          ) : (
            <>
              <div className="space-y-3">
                {enabled.map((pid) => (
                  <EditorCaptionCard
                    key={pid}
                    platformId={pid}
                    caption={captions[pid] ?? ""}
                    onCaptionChange={(v) => handleCaptionChange(pid, v)}
                    onIterate={(instruction) =>
                      iterateMutation.mutate({ platform: pid, instruction })
                    }
                    iterating={
                      iterateMutation.isPending && iterateMutation.variables?.platform === pid
                    }
                  />
                ))}
              </div>
              {enabled.length > 1 && (
                <div className="t-micro ink-muted -mt-3">
                  Iterating rewrites only this platform — the other{" "}
                  {enabled.length === 2
                    ? "caption holds"
                    : `${enabled.length - 1} captions hold`}{" "}
                  still.
                </div>
              )}
              {historyPlatform && (
                <EditorHistory
                  iterations={iterations}
                  platforms={enabled}
                  platform={historyPlatform}
                  onPlatformChange={setHistoryPlatform}
                  onRestore={(iterationId) =>
                    revertMutation.mutate({ platform: historyPlatform, iterationId })
                  }
                  onDelete={(iterationId) => deleteIterationMutation.mutate(iterationId)}
                />
              )}
            </>
          )}

          {noAlt && (
            <div className="border-cream-300 bg-cream-100 rounded-xl border p-3.5">
              <label
                id="alt-blocker-note"
                htmlFor="alt-text-input"
                className="t-caption text-cream-ink-deep block font-medium"
              >
                Add alt text to 1 image before publishing
              </label>
              <p className="t-micro text-cream-ink mt-0.5">
                Describe the image so screen readers can carry it too.
              </p>
              <div className="mt-2 flex gap-2">
                <Input
                  id="alt-text-input"
                  value={altDraft}
                  onChange={(e) => setAltDraft(e.target.value)}
                  placeholder="e.g. Tabby resting under the walnut tree at dusk"
                  className="bg-card h-9 flex-1"
                />
                <Button
                  size="sm"
                  variant="cream"
                  onClick={() => altMutation.mutate(altDraft.trim())}
                  disabled={!altDraft.trim() || altMutation.isPending}
                >
                  Save alt text
                </Button>
              </div>
            </div>
          )}

          <div className="bg-warm flex h-11 items-center justify-between gap-3 rounded-lg px-3">
            <span className="t-body-sm ink">Require review before release</span>
            <Toggle
              size="sm"
              checked={row.require_review}
              onChange={(value) => reviewMutation.mutate(value)}
              aria-label="Require review before release"
            />
          </div>
        </div>
      )}
    </GVSheet>
  );
}
