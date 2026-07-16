import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Crop, Eye, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api, type MediaItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { TextLink } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { errorDetail } from "./media-utils";

interface CropCombo {
  platform: string;
  format: string;
  ratio: string;
}

/**
 * The ONLY valid platform/format combos — 1:1 with the backend's
 * PLATFORM_DIMENSIONS. Do not invent others.
 */
const CROP_COMBOS: CropCombo[] = [
  { platform: "instagram", format: "post", ratio: "1:1" },
  { platform: "instagram", format: "story", ratio: "9:16" },
  { platform: "facebook", format: "post", ratio: "1.91:1" },
  { platform: "facebook", format: "story", ratio: "9:16" },
  { platform: "tiktok", format: "story", ratio: "9:16" },
  { platform: "linkedin", format: "post", ratio: "1.91:1" },
];

const PLATFORM_NAMES: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
};

function comboLabel(platform: string, format: string): string {
  const p =
    PLATFORM_NAMES[platform] ?? platform.charAt(0).toUpperCase() + platform.slice(1);
  const f = format.charAt(0).toUpperCase() + format.slice(1);
  return `${p} · ${f}`;
}

function comboKey(c: CropCombo): string {
  return `${c.platform}:${c.format}`;
}

/**
 * "Platform versions" inspector section — generate + view backend smart
 * crops. No drag-crop editor, no text overlays (backend has no support).
 */
export function PlatformVersions({ media }: { media: MediaItem }) {
  const isImage = media.mime_type.startsWith("image/");
  const queryClient = useQueryClient();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(
    () => new Set(CROP_COMBOS.map(comboKey)),
  );
  const [generateError, setGenerateError] = useState<string | null>(null);

  const adapted = useQuery({
    queryKey: ["media", "adapted", media.id],
    queryFn: () => api.getAdaptedVersions(media.id),
    enabled: isImage,
  });

  const selectedCombos = CROP_COMBOS.filter((c) => selectedKeys.has(comboKey(c)));

  const generate = useMutation({
    mutationFn: async (combos: CropCombo[]) => {
      // Group by platform so each call's cross-product is exactly the
      // chosen combos — never over-generates unselected pairs.
      const byPlatform = new Map<string, string[]>();
      for (const c of combos) {
        byPlatform.set(c.platform, [...(byPlatform.get(c.platform) ?? []), c.format]);
      }
      for (const [platform, formats] of byPlatform) {
        await api.adaptMedia(media.id, [platform], formats);
      }
    },
    onSuccess: () => {
      setGenerateError(null);
      setPickerOpen(false);
      toast.success("Platform versions ready");
    },
    onError: (err) => setGenerateError(errorDetail(err, "Couldn't generate crops")),
    // Invalidate on settle (not just success): a mid-sequence failure may
    // still have created some crops — render them alongside the error.
    onSettled: () =>
      void queryClient.invalidateQueries({ queryKey: ["media", "adapted", media.id] }),
  });

  function toggleCombo(key: string) {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const versions = adapted.data?.adapted ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="t-micro font-medium tracking-wider text-sage-600 uppercase dark:text-sage-300">
          Platform versions
        </div>
        {isImage && (
          <button
            type="button"
            onClick={() => setPickerOpen((v) => !v)}
            aria-expanded={pickerOpen}
            className="fr flex items-center gap-1 rounded-sm text-[11px] font-medium text-sage-600 hover:text-sage-700 dark:text-sage-300 dark:hover:text-sage-200"
          >
            <Crop size={11} strokeWidth={1.75} aria-hidden="true" />
            Generate crops
          </button>
        )}
      </div>

      {!isImage ? (
        <p className="t-caption ink-muted">Crops are available for photos only.</p>
      ) : (
        <>
          {pickerOpen && (
            <div className="bg-warm border-hair space-y-2 rounded-lg p-2.5">
              <div className="flex flex-wrap gap-1.5">
                {CROP_COMBOS.map((c) => {
                  const key = comboKey(c);
                  const active = selectedKeys.has(key);
                  return (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={active}
                      onClick={() => toggleCombo(key)}
                      className={cn(
                        "fr t-caption flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium transition",
                        active
                          ? "border-sage-100 bg-sage-50 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-100"
                          : "bg-card border-hair ink-muted",
                      )}
                    >
                      {active && <Check size={10} strokeWidth={2} aria-hidden="true" />}
                      {comboLabel(c.platform, c.format)}{" "}
                      <span className="ink-muted">{c.ratio}</span>
                    </button>
                  );
                })}
              </div>
              <Button
                size="sm"
                className="fr"
                disabled={selectedCombos.length === 0 || generate.isPending}
                aria-busy={generate.isPending}
                onClick={() => generate.mutate(selectedCombos)}
              >
                {generate.isPending ? (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Crop size={12} strokeWidth={1.75} aria-hidden="true" />
                )}
                Generate {selectedCombos.length}
              </Button>
            </div>
          )}

          {adapted.isLoading || generate.isPending ? (
            <div
              role="status"
              aria-label="Loading platform versions"
              className="space-y-1.5"
            >
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton h-12 rounded-lg" />
              ))}
            </div>
          ) : versions.length === 0 ? (
            <p className="t-caption ink-muted">
              No platform versions yet. Crops sized for each platform's feed.
            </p>
          ) : (
            <div className="space-y-1.5">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className="bg-card border-hair flex items-center gap-2.5 rounded-lg p-2"
                >
                  <img src={`/${v.adapted_path}`} alt="" className="h-10 w-auto rounded" />
                  <div className="min-w-0 flex-1">
                    <div className="ink truncate text-xs font-medium">
                      {comboLabel(v.platform, v.format)}
                    </div>
                    <div className="ink-muted font-mono text-[10.5px]">
                      {v.width} × {v.height}
                    </div>
                  </div>
                  <TextLink
                    className="t-caption shrink-0"
                    onClick={() => window.open(`/${v.adapted_path}`, "_blank", "noopener")}
                  >
                    View
                  </TextLink>
                </div>
              ))}
            </div>
          )}

          {generateError && (
            <p role="alert" className="t-caption text-terra-600 dark:text-terra-300">
              {generateError}
            </p>
          )}
        </>
      )}

      <p className="t-micro ink-muted flex items-center gap-1">
        <Eye size={10} strokeWidth={1.75} aria-hidden="true" className="shrink-0" />
        Preview is approximate — final crop & compression are set by each platform.
      </p>
    </div>
  );
}
