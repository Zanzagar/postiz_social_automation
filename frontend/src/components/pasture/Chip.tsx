import type * as React from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { pillarColor, type PillarLike } from "@/lib/pillars";

export type ChipTone = "neutral" | "sage" | "terra" | "cream";

const CHIP_TONES: Record<ChipTone, string> = {
  neutral: "bg-card border-hair ink",
  sage: "border border-sage-100 bg-sage-50 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-100",
  terra:
    "border border-terra-200 bg-terra-50 text-terra-700 dark:border-terra-600 dark:bg-terra-700/30 dark:text-terra-200",
  cream:
    "border border-cream-300 bg-cream-100 text-cream-ink dark:border-cream-400/40 dark:bg-cream-400/15",
};

interface ChipProps {
  tone?: ChipTone;
  /** CSS color for a small leading dot */
  dot?: string;
  /** Arbitrary leading node (e.g. a PlatformDot) */
  leading?: React.ReactNode;
  removable?: boolean;
  onRemove?: () => void;
  children: React.ReactNode;
  className?: string;
}

/** Unified chip family — status, pillar, platform, and hashtag chips. */
export function Chip({
  tone = "neutral",
  dot,
  leading,
  removable,
  onRemove,
  children,
  className,
}: ChipProps) {
  return (
    <span
      className={cn(
        "t-caption inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-medium",
        CHIP_TONES[tone] ?? CHIP_TONES.neutral,
        className,
      )}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: dot }}
          aria-hidden="true"
        />
      )}
      {leading}
      <span>{children}</span>
      {removable && (
        <button
          type="button"
          aria-label="Remove"
          onClick={onRemove}
          className="fr -mr-1 ml-0.5 rounded-full p-0.5 hover:bg-black/5 dark:hover:bg-white/10"
        >
          <X size={11} strokeWidth={1.75} aria-hidden="true" />
        </button>
      )}
    </span>
  );
}

interface PillarChipProps {
  /** Pillar object (from GET /api/pillars) or just its name */
  pillar: PillarLike | string;
  size?: "xs" | "sm";
  className?: string;
}

/** Pillar chip — dot colored via pillarColor(), name label. */
export function PillarChip({ pillar, size = "sm", className }: PillarChipProps) {
  const name = typeof pillar === "string" ? pillar : pillar.name;
  if (!name) return null;
  const sz = size === "xs" ? "t-micro px-1.5 py-0.5" : "t-caption px-2 py-0.5";
  return (
    <span
      className={cn(
        "bg-card border-hair inline-flex items-center gap-1.5 rounded-full font-medium",
        sz,
        className,
      )}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: pillarColor(pillar) }}
        aria-hidden="true"
      />
      <span className="ink">{name}</span>
    </span>
  );
}
