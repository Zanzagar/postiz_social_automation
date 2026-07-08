import { useNavigate } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { Flame } from "lucide-react";

import { SkeletonText, TextLink } from "@/components/pasture";
import type { FestivalItem } from "@/hooks/useDashboardData";
import { DashCard } from "./DashCard";

interface HorizonCardProps {
  festivals: FestivalItem[];
  isLoading?: boolean;
}

/** "On the horizon" — the next three festivals with cream date boxes. */
export function HorizonCard({ festivals, isLoading }: HorizonCardProps) {
  const navigate = useNavigate();

  return (
    <DashCard
      title="On the horizon"
      right={
        <Flame
          size={15}
          strokeWidth={1.75}
          className="text-terra-500"
          aria-hidden="true"
        />
      }
      bodyClassName="space-y-3 pt-2"
    >
      {isLoading ? (
        <SkeletonText lines={3} />
      ) : festivals.length === 0 ? (
        <p className="t-caption ink-muted py-2">No festivals on the horizon.</p>
      ) : (
        festivals.map(({ festival, daysUntil }) => {
          const date = parseISO(festival.date);
          return (
            <div key={`${festival.name}-${festival.date}`} className="flex items-center gap-3">
              <div className="flex h-10 w-10 flex-col items-center justify-center rounded-lg border border-cream-300 bg-cream-100 leading-none dark:border-cream-400/40 dark:bg-cream-400/15">
                <span className="t-micro text-cream-ink font-semibold uppercase">
                  {format(date, "MMM")}
                </span>
                <span className="t-title-sm text-cream-ink font-serif">
                  {format(date, "d")}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="t-body-sm ink font-medium">{festival.name}</div>
                <div className="t-caption ink-muted truncate">{festival.significance}</div>
              </div>
              <div className="t-caption ink-muted font-mono">
                {daysUntil === 0 ? "today" : `in ${daysUntil}d`}
              </div>
            </div>
          );
        })
      )}
      <div className="pt-1">
        <TextLink className="t-caption" onClick={() => navigate("/suggestions")}>
          See all suggestions →
        </TextLink>
      </div>
    </DashCard>
  );
}
