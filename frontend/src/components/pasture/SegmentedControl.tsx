import { cn } from "@/lib/utils";

export type SegmentedOption = string | { id: string; label?: string };

interface SegmentedControlProps {
  /** 2–4 short options; for more (or long labels) use a Select instead */
  options: SegmentedOption[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
  "aria-label"?: string;
}

/**
 * Single-select view switch (e.g. Calendar week/month/list).
 * bg-warm track; active option gets bg-card + shadow-card.
 */
export function SegmentedControl({
  options,
  value,
  onChange,
  className,
  "aria-label": ariaLabel,
}: SegmentedControlProps) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        "bg-warm border-hair inline-flex items-center rounded-lg p-0.5",
        className,
      )}
    >
      {options.map((o) => {
        const id = typeof o === "string" ? o : o.id;
        const label = typeof o === "string" ? o : (o.label ?? o.id);
        const active = id === value;
        return (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(id)}
            className={cn(
              "fr t-body-sm h-7 rounded-md px-3 font-medium transition-colors",
              active
                ? "bg-card shadow-card text-sage-800 dark:text-sage-100"
                : "ink-muted hover:text-sage-700 dark:hover:text-sage-300",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
