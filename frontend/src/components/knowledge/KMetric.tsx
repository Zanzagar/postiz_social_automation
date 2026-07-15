import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { SkeletonText } from "@/components/pasture";

interface KMetricProps {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
  /** Cream warning styling (used when coverage gaps exist) */
  warn?: boolean;
  loading?: boolean;
}

/** Knowledge metric card — label, serif numeral, caption sub-line. */
export function KMetric({ label, value, sub, icon: Icon, warn, loading }: KMetricProps) {
  return (
    <div
      className={cn(
        "bg-card shadow-card rounded-xl p-3.5",
        warn
          ? "border border-cream-300 dark:border-cream-400/40"
          : "border-hair",
      )}
    >
      <div className="flex items-center gap-1.5">
        <Icon
          size={11}
          strokeWidth={1.75}
          aria-hidden="true"
          className={warn ? "text-cream-ink" : "text-sage-600 dark:text-sage-300"}
        />
        <div
          className={cn(
            "t-label",
            warn ? "text-cream-ink" : "text-sage-700 dark:text-sage-300",
          )}
        >
          {label}
        </div>
      </div>
      {loading ? (
        <SkeletonText lines={2} className="mt-2" />
      ) : (
        <>
          <div className="t-h2 mt-1.5 font-medium text-sage-800 dark:text-sage-100">
            {value}
          </div>
          {sub && <div className="t-caption ink-muted mt-1 leading-snug">{sub}</div>}
        </>
      )}
    </div>
  );
}
