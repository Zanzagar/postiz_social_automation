import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileText, Save, Sprout, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { GVSheet, PageHeader } from "@/components/pasture";
import { ComposeStage } from "@/components/create/ComposeStage";
import { GenerateStage } from "@/components/create/GenerateStage";
import { RefineStage } from "@/components/create/RefineStage";
import { StageRail } from "@/components/create/StageRail";
import { useLocalDraft, type CreateStage } from "@/hooks/useLocalDraft";
import {
  api,
  request,
  type GenerateRequest,
  type Template,
} from "@/lib/api";

/** A catalog item preloaded into compose via /create?media={id}. */
interface PendingMedia {
  id: number;
  url: string;
  thumbnailUrl: string;
  filename: string;
}

/**
 * Contract "URL construction": drive://<id> streams from the Drive proxy;
 * local paths (media/<file>) are served from the static mount.
 */
function mediaFileUrl(localPath: string): string {
  if (localPath.startsWith("drive://")) {
    return `/api/media/drive/file/${localPath.slice("drive://".length)}`;
  }
  return `/${localPath}`;
}

/**
 * Create flow — three rooms: Compose → Generate (live SSE) → Refine.
 * Compose state persists to localStorage (useLocalDraft) so an
 * in-progress post survives session expiry; cleared on save/send.
 */
export function CreatePage() {
  const { draft, update, clear } = useLocalDraft();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [templateSheetOpen, setTemplateSheetOpen] = useState(false);

  // --- Media-library intake (/create?media={id}) ---
  const [searchParams] = useSearchParams();
  const mediaParam = searchParams.get("media");
  const mediaParamId =
    mediaParam && /^\d+$/.test(mediaParam) ? Number(mediaParam) : null;

  const [pendingMedia, setPendingMedia] = useState<PendingMedia | null>(null);
  const pendingMediaRef = useRef<PendingMedia | null>(null);
  useEffect(() => {
    pendingMediaRef.current = pendingMedia;
  }, [pendingMedia]);
  const preloadedIdRef = useRef<number | null>(null);

  // A restored mid-flow draft (generate/refine) must never be clobbered by a
  // ?media= preload — captured once at mount from the restored draft's stage.
  const [mediaIntakeBlocked] = useState(
    () => mediaParamId !== null && draft.stage !== "compose",
  );
  const blockedToastShownRef = useRef(false);
  useEffect(() => {
    if (mediaIntakeBlocked && !blockedToastShownRef.current) {
      blockedToastShownRef.current = true;
      toast.error(
        "You already have a draft in progress — save or discard it first, then use the library photo.",
      );
    }
  }, [mediaIntakeBlocked]);

  const { data: mediaDetail, isError: mediaLoadFailed } = useQuery({
    queryKey: ["media", "detail", mediaParamId],
    queryFn: () => api.getMediaDetail(mediaParamId!),
    enabled: mediaParamId !== null && !mediaIntakeBlocked,
  });

  // Preload the catalog image into compose exactly once per media id.
  useEffect(() => {
    if (mediaIntakeBlocked) return;
    if (!mediaDetail) return;
    const m = mediaDetail.media;
    if (preloadedIdRef.current === m.id) return;
    preloadedIdRef.current = m.id;
    const url = mediaFileUrl(m.local_path);
    setPendingMedia({
      id: m.id,
      url,
      thumbnailUrl: m.thumbnail_path ? `/${m.thumbnail_path}` : url,
      filename: m.filename,
    });
    update({ mediaUrl: url, altText: m.alt_text ?? "" });
  }, [mediaDetail, mediaIntakeBlocked, update]);

  useEffect(() => {
    if (mediaLoadFailed) {
      toast.error("Couldn't load that media item — starting without it.");
    }
  }, [mediaLoadFailed]);

  // If the photo is removed or replaced in compose, drop the pending attach.
  useEffect(() => {
    if (pendingMedia && draft.mediaUrl !== pendingMedia.url) {
      setPendingMedia(null);
    }
  }, [draft.mediaUrl, pendingMedia]);

  /** Attach the preloaded catalog item to the freshly created row (once). */
  async function attachPendingMedia(rowId: number) {
    const pending = pendingMediaRef.current;
    if (!pending) return;
    pendingMediaRef.current = null;
    setPendingMedia(null);
    try {
      await api.attachMedia(rowId, pending.id);
    } catch {
      // Non-fatal: the draft row exists either way.
      toast.error("Draft saved, but the library photo couldn't be attached.");
    }
  }

  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars", "active"],
    queryFn: () => api.getPillars(true),
  });
  const { data: templates = [] } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.getTemplates(),
  });
  const { data: festivals = [] } = useQuery({
    queryKey: ["festivals", draft.scheduledDate],
    queryFn: () => api.getFestivals(draft.scheduledDate, draft.scheduledDate),
    enabled: !!draft.scheduledDate,
  });

  const generateRequest: GenerateRequest = {
    raw_text: draft.seed,
    media_url: draft.mediaUrl || null,
    platforms: draft.platforms,
    scheduled_date: draft.scheduledDate,
    content_pillar: draft.pillar || null,
  };

  const canGenerate = draft.seed.trim().length > 0 && draft.platforms.length > 0;

  function startGenerate() {
    if (!canGenerate) return;
    setNotice(null);
    setError(null);
    update({ stage: "generate" });
  }

  function handleGenerated(rowId: number | null, captions: Record<string, string>) {
    if (rowId !== null) void attachPendingMedia(rowId);
    update({ rowId, captions, stage: "refine" });
  }

  function handleStageNav(next: CreateStage) {
    if (next === draft.stage) return;
    // Can't jump into a live generation stream, or into refine with nothing to refine.
    if (next === "generate") return;
    if (next === "refine" && Object.keys(draft.captions).length === 0) return;
    update({ stage: next });
  }

  async function saveWithoutGenerating() {
    if (!canGenerate) return;
    setIsSaving(true);
    setError(null);
    try {
      const result = await request<{
        captions: Record<string, string>;
        row_id?: number;
      }>("/api/generate-sync?skip_ai=true", {
        method: "POST",
        body: JSON.stringify(generateRequest),
      });
      if (result.row_id && draft.mediaUrl && draft.altText.trim()) {
        await api.setAltText(result.row_id, draft.altText.trim());
      }
      if (result.row_id) {
        await attachPendingMedia(result.row_id);
      }
      clear();
      setNotice("Saved to Drafts — find it under Review Drafts.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveRefinedToDrafts() {
    if (!draft.rowId) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.editDraft(draft.rowId, draft.captions);
      if (draft.mediaUrl && draft.altText.trim()) {
        await api.setAltText(draft.rowId, draft.altText.trim());
      }
      clear();
      setNotice("Saved to Drafts — find it under Review Drafts.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }

  async function sendToPostiz() {
    setIsSending(true);
    setError(null);
    try {
      const result = await api.sendToPostiz({
        captions: draft.captions,
        media_url: draft.mediaUrl || null,
        scheduled_at: draft.scheduledDate,
      });
      clear();
      setNotice(`Sent to Postiz: ${result.draft_ids.length} draft(s) created`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    } finally {
      setIsSending(false);
    }
  }

  function applyTemplate(t: Template) {
    update({
      seed: t.raw_text_template ?? "",
      pillar: t.pillar ?? draft.pillar,
      scheduledTime: t.schedule_time ?? draft.scheduledTime,
      stage: "compose",
    });
    setTemplateSheetOpen(false);
  }

  const headerSave = draft.stage === "refine" && draft.rowId ? saveRefinedToDrafts : saveWithoutGenerating;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <PageHeader
        greeting="Compose"
        title="A new post begins with a single line."
        subtitle="Describe what you want to share. Claude shapes it for every platform. You refine."
        icon={Sprout}
        right={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={headerSave}
              disabled={isSaving || (draft.stage === "refine" ? !draft.rowId : !canGenerate)}
            >
              <Save size={12} strokeWidth={1.75} aria-hidden="true" />
              Save draft
            </Button>
            <Button variant="outline" size="sm" onClick={() => setTemplateSheetOpen(true)}>
              Use a template
            </Button>
          </>
        }
      />
      <StageRail stage={draft.stage} onStage={handleStageNav} />

      {notice && (
        <div
          role="status"
          className="t-body-sm mx-8 mt-4 rounded-lg border border-sage-200 bg-sage-50 px-3 py-2 text-sage-700 dark:border-sage-700 dark:bg-sage-800/60 dark:text-sage-200"
        >
          {notice}
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="t-body-sm mx-8 mt-4 rounded-lg border border-terra-200 bg-terra-50 px-3 py-2 text-terra-700 dark:border-terra-600 dark:bg-terra-700/20 dark:text-terra-200"
        >
          {error}
        </div>
      )}

      {pendingMedia && draft.stage === "compose" && (
        <div className="bg-card border-hair mx-8 mt-4 flex items-center gap-2.5 self-start rounded-lg px-2.5 py-1.5">
          <img
            src={pendingMedia.thumbnailUrl}
            alt=""
            className="h-8 w-8 rounded object-cover"
          />
          <div className="min-w-0">
            <div className="t-caption ink max-w-[240px] truncate font-medium">
              {pendingMedia.filename}
            </div>
            <div className="t-micro ink-muted">From the media library</div>
          </div>
          <button
            type="button"
            aria-label={`Remove ${pendingMedia.filename}`}
            onClick={() => {
              setPendingMedia(null);
              update({ mediaUrl: "", altText: "" });
            }}
            className="fr ink-muted ml-1 flex h-6 w-6 items-center justify-center rounded-md hover:bg-sage-50 dark:hover:bg-sage-800"
          >
            <X size={13} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        {draft.stage === "compose" && (
          <div className="flex-1 overflow-y-auto">
            <ComposeStage
              draft={draft}
              update={update}
              pillars={pillars}
              festivals={festivals}
              canGenerate={canGenerate}
              onGenerate={startGenerate}
              onSaveWithoutGenerating={saveWithoutGenerating}
              isSaving={isSaving}
            />
          </div>
        )}
        {draft.stage === "generate" && (
          <div className="flex-1 overflow-y-auto">
            <GenerateStage
              generateRequest={generateRequest}
              pillar={draft.pillar}
              onDone={handleGenerated}
            />
          </div>
        )}
        {draft.stage === "refine" && (
          <RefineStage
            draft={draft}
            update={update}
            onSaveDraft={saveRefinedToDrafts}
            onSend={sendToPostiz}
            isSaving={isSaving}
            isSending={isSending}
          />
        )}
      </div>

      {templateSheetOpen && (
        <GVSheet title="Use a template" onClose={() => setTemplateSheetOpen(false)}>
          {templates.length === 0 ? (
            <p className="t-body ink-muted">
              No templates yet — create one under Templates to reuse a post structure.
            </p>
          ) : (
            <div className="space-y-2">
              {templates.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => applyTemplate(t)}
                  className="fr bg-card border-hair flex w-full items-start gap-3 rounded-xl px-4 py-3 text-left transition hover:border-sage-300"
                >
                  <FileText
                    size={16}
                    strokeWidth={1.75}
                    className="mt-0.5 shrink-0 text-sage-600 dark:text-sage-300"
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="t-ui ink block font-medium">{t.name}</span>
                    {t.raw_text_template && (
                      <span className="t-caption ink-muted block truncate">
                        {t.raw_text_template}
                      </span>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
        </GVSheet>
      )}
    </div>
  );
}
