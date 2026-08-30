import { useRef, useState } from "react";
import {
  Check,
  Flame,
  Image as ImageIcon,
  Leaf,
  Lightbulb,
  Loader2,
  Save,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PillarChip, PlatformDot } from "@/components/pasture";
import { api, type Festival, type Pillar } from "@/lib/api";
import { PLATFORMS } from "@/lib/platforms";
import { pillarColor } from "@/lib/pillars";
import { cn } from "@/lib/utils";
import type { CreateDraft } from "@/hooks/useLocalDraft";

const SEED_MAX = 2000;

interface ComposeStageProps {
  draft: CreateDraft;
  update: (patch: Partial<CreateDraft>) => void;
  pillars: Pillar[];
  festivals: Festival[];
  canGenerate: boolean;
  onGenerate: () => void;
  onSaveWithoutGenerating: () => void;
  isSaving: boolean;
}

/** Stage 1 — plant the seed: text, platforms, pillar, schedule, media. */
export function ComposeStage({
  draft,
  update,
  pillars,
  festivals,
  canGenerate,
  onGenerate,
  onSaveWithoutGenerating,
  isSaving,
}: ComposeStageProps) {
  const [focus, setFocus] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const festival = festivals.find((f) => f.date === draft.scheduledDate);

  async function handleFile(file: File) {
    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await api.uploadFile(file);
      update({ mediaUrl: result.url });
    } catch {
      setUploadError("Failed to upload file");
    } finally {
      setIsUploading(false);
    }
  }

  function togglePlatform(id: string) {
    update({
      platforms: draft.platforms.includes(id)
        ? draft.platforms.filter((p) => p !== id)
        : [...draft.platforms, id],
    });
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-4 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-5">
        {/* Seed */}
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <label htmlFor="seed" className="t-label text-sage-700 dark:text-sage-300">
              The seed of an idea
            </label>
            <span className="t-caption ink-muted">
              {draft.seed.length}/{SEED_MAX}
            </span>
          </div>
          <div
            className={cn(
              "bg-card relative overflow-hidden rounded-2xl border transition-all",
              focus
                ? "border-sage-400 shadow-[0_0_0_3px_rgba(74,124,89,0.12)]"
                : "border-sage-200 dark:border-sage-700",
            )}
          >
            <div className="pointer-events-none absolute -top-3 -right-3 opacity-[0.07]">
              <Leaf size={80} strokeWidth={1.75} aria-hidden="true" />
            </div>
            <Textarea
              id="seed"
              rows={5}
              maxLength={SEED_MAX}
              placeholder={
                "A sentence is enough — Claude will expand it for each platform.\ne.g. 'Temple program and feast for Rama Navami on March 26'"
              }
              value={draft.seed}
              onChange={(e) => update({ seed: e.target.value })}
              onFocus={() => setFocus(true)}
              onBlur={() => setFocus(false)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && canGenerate) {
                  e.preventDefault();
                  onGenerate();
                }
              }}
              className="t-body min-h-[140px] border-0 bg-transparent p-5 font-serif leading-relaxed shadow-none focus-visible:ring-0"
            />
            <div className="flex items-center gap-1 border-t border-sage-100 bg-sage-50/40 px-3 py-2 dark:border-sage-800 dark:bg-sage-900/40">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="fr t-caption flex h-7 items-center gap-1.5 rounded-md px-2.5 text-sage-700 hover:bg-card dark:text-sage-300"
              >
                <ImageIcon size={11} strokeWidth={1.75} aria-hidden="true" />
                Photo
              </button>
              <span className="mx-1 h-4 w-px bg-sage-200 dark:bg-sage-700" aria-hidden="true" />
              <div className="t-caption ink-muted flex items-center gap-1">
                <Sparkles size={10} strokeWidth={1.75} className="text-sage-500" aria-hidden="true" />
                <span>Tip: lead with a sensory detail</span>
              </div>
              <div className="t-micro ink-muted ml-auto font-mono">⌘⏎ to generate</div>
            </div>
          </div>
        </div>

        {/* Platforms */}
        <div>
          <span className="t-label mb-2 block text-sage-700 dark:text-sage-300">
            Send to these platforms
          </span>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Platforms">
            {PLATFORMS.map((pl) => {
              const on = draft.platforms.includes(pl.id);
              return (
                <button
                  key={pl.id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => togglePlatform(pl.id)}
                  className={cn(
                    "fr flex h-9 items-center gap-2 rounded-lg border px-3 transition",
                    on
                      ? "shadow-card border-sage-500 bg-sage-500 text-white"
                      : "bg-card border-hair ink hover:border-sage-300",
                  )}
                >
                  <PlatformDot id={pl.id} size={12} />
                  <span className="t-ui font-medium">{pl.label}</span>
                  {on && <Check size={13} strokeWidth={1.75} aria-hidden="true" />}
                </button>
              );
            })}
          </div>
          <div className="t-caption ink-muted mt-1.5">
            {draft.platforms.length === PLATFORMS.length
              ? `All ${PLATFORMS.length} selected — Claude will write a version in each platform's native voice.`
              : `${draft.platforms.length} selected — Claude writes a version in each platform's native voice.`}
          </div>
        </div>

        {/* Pillar + schedule */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <span className="t-label mb-2 block text-sage-700 dark:text-sage-300">
              Content pillar
            </span>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Content pillar">
              {pillars.map((p) => {
                const on = draft.pillar === p.name;
                return (
                  <button
                    key={p.id}
                    type="button"
                    aria-pressed={on}
                    onClick={() => update({ pillar: on ? "" : p.name })}
                    className={cn(
                      "t-body-sm fr flex h-8 items-center gap-2 rounded-lg border px-2.5 transition",
                      on
                        ? "bg-card shadow-card border-sage-400 text-sage-800 dark:border-sage-500 dark:text-sage-100"
                        : "bg-card border-hair ink hover:border-sage-200",
                    )}
                  >
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ background: pillarColor(p) }}
                      aria-hidden="true"
                    />
                    <span className="whitespace-nowrap">{p.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <span className="t-label mb-2 block text-sage-700 dark:text-sage-300">Schedule</span>
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="date"
                aria-label="Schedule date"
                value={draft.scheduledDate}
                onChange={(e) => update({ scheduledDate: e.target.value })}
              />
              <Input
                type="time"
                aria-label="Schedule time"
                value={draft.scheduledTime}
                onChange={(e) => update({ scheduledTime: e.target.value })}
              />
            </div>
            {festival && (
              <div className="t-caption ink-muted mt-1.5 flex items-center gap-1">
                <Flame size={11} strokeWidth={1.75} className="text-terra-500" aria-hidden="true" />
                {festival.name} falls on this day
              </div>
            )}
          </div>
        </div>

        {/* Media */}
        <div>
          <span className="t-label mb-2 block text-sage-700 dark:text-sage-300">Media</span>
          <div className="flex flex-wrap items-start gap-2">
            {draft.mediaUrl && (
              <div className="relative aspect-square w-24 overflow-hidden rounded-lg border-2 border-sage-500">
                <img
                  src={draft.mediaUrl}
                  alt={draft.altText || "Selected media"}
                  className="h-full w-full object-cover"
                />
                <span className="absolute top-1.5 left-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-sage-500 text-white">
                  <Check size={12} strokeWidth={1.75} aria-hidden="true" />
                </span>
                <button
                  type="button"
                  aria-label="Remove media"
                  onClick={() => update({ mediaUrl: "", altText: "" })}
                  className="fr absolute top-1.5 right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-sage-900/70 text-white"
                >
                  <X size={12} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </div>
            )}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="fr ink-muted flex aspect-square w-24 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-sage-200 transition hover:border-sage-400 hover:bg-sage-50/50 dark:border-sage-700"
            >
              {isUploading ? (
                <Loader2 size={16} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
              ) : (
                <Upload size={16} strokeWidth={1.75} aria-hidden="true" />
              )}
              <span className="t-micro">{isUploading ? "Uploading…" : "Upload"}</span>
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            aria-label="Upload media file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
          {uploadError && (
            <p className="t-caption mt-1.5 text-terra-700" role="alert">
              {uploadError}
            </p>
          )}
          <div className="mt-2 max-w-sm">
            <label htmlFor="media-url" className="t-caption ink-muted block">
              Or paste a media URL
            </label>
            <Input
              id="media-url"
              value={draft.mediaUrl}
              onChange={(e) => update({ mediaUrl: e.target.value })}
              placeholder="https://drive.google.com/..."
            />
          </div>
          {draft.mediaUrl && (
            <div className="mt-2 max-w-sm">
              <label htmlFor="alt-text" className="t-caption ink-muted block">
                Alt text
              </label>
              <Input
                id="alt-text"
                value={draft.altText}
                onChange={(e) => update({ altText: e.target.value })}
                placeholder="Describe the image for screen readers"
              />
            </div>
          )}
        </div>
      </div>

      {/* Aside */}
      <aside className="min-w-0 space-y-4">
        <div className="rounded-xl border border-cream-300 bg-cream-100/60 px-5 py-4 dark:border-cream-400/40 dark:bg-cream-400/10">
          <div className="mb-2 flex items-center gap-2">
            <Lightbulb size={14} strokeWidth={1.75} className="text-cream-ink" aria-hidden="true" />
            <span className="t-label text-cream-ink">Knowledge nudges</span>
          </div>
          <div className="t-body-sm space-y-2 leading-relaxed text-cream-ink-deep">
            <p>
              Brand voice is <span className="font-medium">warm, welcoming, grounded</span> — lead
              with cows and farm, not religion.
            </p>
            {draft.pillar && (
              <p>
                You're posting to the <PillarChip pillar={draft.pillar} size="xs" /> pillar.
              </p>
            )}
          </div>
        </div>

        <div className="bg-card border-hair rounded-xl px-5 py-4">
          <div className="t-label mb-1 text-sage-700/70 dark:text-sage-300/70">Ready to plant</div>
          <div className="t-body-sm ink leading-relaxed">
            {draft.platforms.length === 0 ? (
              <>
                Pick at least one platform and Claude will draft a caption in
                each platform's voice.
              </>
            ) : (
              <>
                Claude will draft {draft.platforms.length} platform-specific{" "}
                {draft.platforms.length === 1 ? "caption" : "captions"} from your
                seed — usually 30–90 seconds. You'll refine{" "}
                {draft.platforms.length === 1 ? "it" : "each one"} next.
              </>
            )}
          </div>
          <Button
            size="lg"
            className="fr mt-3 w-full"
            onClick={onGenerate}
            disabled={!canGenerate}
          >
            <Sparkles size={15} strokeWidth={1.75} aria-hidden="true" />
            Generate captions
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="fr mt-1 w-full"
            onClick={onSaveWithoutGenerating}
            disabled={!canGenerate || isSaving}
          >
            {isSaving ? (
              <Loader2 size={12} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            ) : (
              <Save size={12} strokeWidth={1.75} aria-hidden="true" />
            )}
            Save as draft without generating
          </Button>
        </div>
      </aside>
    </div>
  );
}
