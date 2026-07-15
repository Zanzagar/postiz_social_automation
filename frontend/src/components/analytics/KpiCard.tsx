import { cn } from "@/lib/utils";
import { Spark } from "./Spark";
import type { AccentTone } from "./format";

interface KpiCardProps {
  label: string;
  /** Pre-formatted display value ("34", "18.2k", "4.8%"). */
  value: string;
  /** Pre-formatted signed delta ("+27%"), or null to omit (unknowable). */
  delta: string | null;
  series: number[];
  accent?: AccentTone;
}

/** Overview KPI card — label, serif value, delta arrow, sparkline. */
export function KpiCard({ label, value, delta, series, accent = "sage" }: KpiCardProps) {
  const up = delta !== null && !delta.startsWith("-");
  return (
    <div className="bg-card border-hair shadow-card rounded-xl p-4">
      <div className="t-label text-sage-600 dark:text-sage-300">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="t-h2 leading-none text-sage-800 dark:text-sage-100">{value}</span>
        {delta !== null && (
          <span
            className={cn(
              "t-body-sm font-medium",
              up
                ? "text-sage-700 dark:text-sage-300"
                : "text-terra-700 dark:text-terra-300",
            )}
          >
            <span aria-hidden="true">{up ? "↑" : "↓"} </span>
            {delta}
          </span>
        )}
      </div>
      <Spark series={series} accent={accent} ariaLabel={`${label} trend`} />
    </div>
  );
}
