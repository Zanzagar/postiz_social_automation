import { pillarColor } from "@/lib/pillars";
import { SkeletonText } from "@/components/pasture";
import type { PillarBalanceRow } from "@/hooks/useDashboardData";
import { DashCard } from "./DashCard";

interface PillarBalanceCardProps {
  rows: PillarBalanceRow[];
  isLoading?: boolean;
}

/** Per-pillar posting mix vs target over the last 30 days. */
export function PillarBalanceCard({ rows, isLoading }: PillarBalanceCardProps) {
  return (
    <DashCard
      title="Pillar balance"
      right={<span className="t-caption ink-muted">last 30 days</span>}
    >
      {isLoading ? (
        <SkeletonText lines={4} />
      ) : rows.length === 0 ? (
        <p className="t-caption ink-muted py-2">
          No pillars yet — add them in Settings.
        </p>
      ) : (
        <div className="space-y-2.5">
          {rows.map((row) => {
            const color = pillarColor({ name: row.name, color: row.color });
            return (
              <div key={row.name}>
                <div className="t-caption mb-1 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: color }}
                      aria-hidden="true"
                    />
                    <span className="ink">{row.name}</span>
                  </span>
                  <span className="ink-muted font-mono">
                    {row.count} · {row.pct}%
                  </span>
                </div>
                <div className="bg-warm relative h-1.5 overflow-visible rounded-full">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.min(row.pct, 100)}%`, background: color }}
                  />
                  {row.target !== null && (
                    <span
                      className="absolute -top-0.5 -bottom-0.5 w-px"
                      style={{
                        left: `${Math.min(row.target, 100)}%`,
                        background: "var(--ink)",
                        opacity: 0.35,
                      }}
                      title={`target ${row.target}%`}
                      aria-hidden="true"
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </DashCard>
  );
}
