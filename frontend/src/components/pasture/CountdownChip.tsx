import { cn } from "@/lib/utils";

function ClockGlyph({ size = 11 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

interface CountdownChipProps {
  /** e.g. "Releases 2:00 PM" */
  label?: string;
  /** e.g. "in 1h 24m" */
  remaining?: string;
  paused?: boolean;
  onToggle?: () => void;
  className?: string;
}

/**
 * Auto-publish rest-window chip. Sage while counting (label + mono remaining
 * + Hold button); flips to cream "Held for review" + Resume when paused.
 * A held post never auto-releases.
 */
export function CountdownChip({
  label = "Releases 2:00 PM",
  remaining = "in 1h 24m",
  paused = false,
  onToggle,
  className,
}: CountdownChipProps) {
  return (
    <span
      className={cn(
        "t-caption inline-flex items-center gap-1.5 rounded-full border py-0.5 pr-1 pl-2 font-medium",
        paused
          ? "border-cream-300 bg-cream-100 text-cream-ink dark:border-cream-400/40 dark:bg-cream-400/15"
          : "border-sage-200 bg-sage-50 text-sage-700 dark:border-sage-600 dark:bg-sage-800 dark:text-sage-100",
        className,
      )}
    >
      <ClockGlyph />
      <span>{paused ? "Held for review" : label}</span>
      {!paused && <span className="t-micro font-mono opacity-70">{remaining}</span>}
      <button
        type="button"
        aria-label={paused ? "Resume auto-release" : "Pause and hold for review"}
        onClick={onToggle}
        className={cn(
          "fr t-micro rounded-full px-1.5 py-0.5 font-semibold transition-colors",
          paused
            ? "bg-cream-300/60 text-cream-ink-deep hover:bg-cream-300"
            : "bg-sage-100 text-sage-800 hover:bg-sage-200 dark:bg-sage-700 dark:text-sage-100 dark:hover:bg-sage-600",
        )}
      >
        {paused ? "Resume" : "Hold"}
      </button>
    </span>
  );
}
