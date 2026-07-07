import { useState } from "react";
import { Check, Eye } from "lucide-react";

import { SegmentedControl } from "@/components/pasture";
import { platformBy } from "@/lib/platforms";
import { hashtagCount } from "./caption-utils";
import { PlatformPreview, type IGVariant } from "./PlatformPreview";

interface PreviewRailProps {
  platform: string;
  caption: string;
  mediaUrl: string | null;
}

/** Static heuristic tone bars — labelled as an estimate, not a measurement. */
const TONE_READING = [
  { label: "Warm", value: 0.85 },
  { label: "Devotional", value: 0.45 },
  { label: "Call-to-action", value: 0.7 },
];

/** Right rail — live platform preview, voice check, tone reading. */
export function PreviewRail({ platform, caption, mediaUrl }: PreviewRailProps) {
  const [igVariant, setIgVariant] = useState<IGVariant>("feed");
  const meta = platformBy(platform);
  const tags = hashtagCount(caption);
  const pressure = meta.ideal > 0 ? caption.length / meta.ideal : 0;

  return (
    <div className="paper bg-warm relative w-[400px] shrink-0 overflow-y-auto p-6">
      <div className="relative">
        <div className="mb-3 flex items-center gap-2">
          <Eye size={14} strokeWidth={1.75} className="text-sage-700 dark:text-sage-300" aria-hidden="true" />
          <span className="t-label text-sage-700 dark:text-sage-300">Live preview</span>
          <span className="t-caption ink-muted ml-auto">as seen on {meta.label}</span>
        </div>

        {platform === "instagram" && (
          <div className="mb-3 flex justify-center">
            <SegmentedControl
              aria-label="Instagram preview variant"
              options={[
                { id: "feed", label: "Feed" },
                { id: "reel", label: "Reel" },
                { id: "story", label: "Story" },
              ]}
              value={igVariant}
              onChange={(id) => setIgVariant(id as IGVariant)}
            />
          </div>
        )}

        <div className="flex justify-center">
          <PlatformPreview
            platform={platform}
            caption={caption}
            image={mediaUrl || undefined}
            variant={platform === "instagram" ? igVariant : undefined}
          />
        </div>

        {/* Fidelity note — preview is representative, not pixel-exact */}
        <div className="t-micro ink-muted mt-2.5 flex items-center justify-center gap-1.5">
          <Eye size={11} strokeWidth={1.75} aria-hidden="true" />
          <span>Preview is approximate — crop, link cards &amp; counts are set by {meta.label}</span>
        </div>

        {/* Voice check */}
        <div className="bg-card/70 mt-4 space-y-2 rounded-xl border border-sage-100 p-3.5 dark:border-sage-800">
          <div className="flex items-center gap-1.5">
            <Check size={13} strokeWidth={1.75} className="text-sage-600 dark:text-sage-300" aria-hidden="true" />
            <span className="t-label text-sage-700 dark:text-sage-300">Voice check</span>
          </div>
          <div className="t-caption ink grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
            <span className="text-sage-600 dark:text-sage-300" aria-hidden="true">
              ✓
            </span>
            <span>
              Leads with <span className="font-medium">the farm</span>, not religion
            </span>
            <span className="text-sage-600 dark:text-sage-300" aria-hidden="true">
              ✓
            </span>
            <span>{meta.label}-native tone &amp; length</span>
            {meta.hashMax === 0 ? (
              tags === 0 ? (
                <>
                  <span className="text-sage-600 dark:text-sage-300" aria-hidden="true">
                    ✓
                  </span>
                  <span>No hashtags — correct for Threads</span>
                </>
              ) : (
                <>
                  <span className="text-terra-500" aria-hidden="true">
                    !
                  </span>
                  <span className="text-terra-700 dark:text-terra-300">
                    {tags} hashtag{tags !== 1 ? "s" : ""} — Threads convention is none
                  </span>
                </>
              )
            ) : tags >= meta.hashMin && tags <= meta.hashMax ? (
              <>
                <span className="text-sage-600 dark:text-sage-300" aria-hidden="true">
                  ✓
                </span>
                <span>
                  {tags} hashtags — within {meta.hashMin}–{meta.hashMax} ideal
                </span>
              </>
            ) : (
              <>
                <span className="text-terra-500" aria-hidden="true">
                  !
                </span>
                <span className="text-terra-700 dark:text-terra-300">
                  {tags} hashtags — aim for {meta.hashMin}–{meta.hashMax} on {meta.label}
                </span>
              </>
            )}
            {pressure > 1 && (
              <>
                <span className="text-terra-500" aria-hidden="true">
                  !
                </span>
                <span className="text-terra-700 dark:text-terra-300">
                  Approaching {meta.label} max length
                </span>
              </>
            )}
          </div>
        </div>

        {/* Tone strip — static heuristic, labelled honestly */}
        <div className="bg-card/70 mt-3 rounded-xl border border-sage-100 px-3.5 py-3 dark:border-sage-800">
          <div className="t-label mb-0.5 text-sage-700 dark:text-sage-300">Tone reading</div>
          <div className="t-micro ink-muted mb-2">Heuristic estimate — trust your ear.</div>
          {TONE_READING.map((t) => (
            <div key={t.label} className="mb-1.5 flex items-center gap-2 last:mb-0">
              <span className="t-caption ink-muted w-24">{t.label}</span>
              <div className="bg-warm h-1.5 flex-1 overflow-hidden rounded-full">
                <div className="h-full bg-sage-500" style={{ width: `${t.value * 100}%` }} />
              </div>
              <span className="t-micro ink-muted font-mono">{Math.round(t.value * 100)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
