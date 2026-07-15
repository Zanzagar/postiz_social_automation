import { cn } from "@/lib/utils";
import type { Insight } from "@/lib/api";

/**
 * "Claude notices" insight card — eyebrow, serif title, body.
 * No CTA button: the design's actions have no wired behavior yet.
 */
export function InsightCard({ tone, title, body }: Insight) {
  const terra = tone === "terra";
  return (
    <div
      className={cn(
        "rounded-xl border p-5",
        terra
          ? "border-terra-200 bg-terra-50 dark:border-terra-600 dark:bg-terra-700/30"
          : "border-sage-200 bg-sage-50 dark:border-sage-700 dark:bg-sage-800/60",
      )}
    >
      <div
        className={cn(
          "t-label",
          terra
            ? "text-terra-700 dark:text-terra-200"
            : "text-sage-700 dark:text-sage-300",
        )}
      >
        Claude notices
      </div>
      <h4
        className={cn(
          "t-title mt-1 leading-snug",
          terra
            ? "text-terra-800 dark:text-terra-100"
            : "text-sage-800 dark:text-sage-100",
        )}
      >
        {title}
      </h4>
      <p
        className={cn(
          "t-body-sm mt-1.5 leading-relaxed",
          terra
            ? "text-terra-700 dark:text-terra-200"
            : "text-sage-700 dark:text-sage-200",
        )}
      >
        {body}
      </p>
    </div>
  );
}
