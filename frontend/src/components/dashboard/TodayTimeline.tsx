import { Link } from "react-router-dom";
import { format } from "date-fns";
import { ArrowRight, Sprout } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Chip,
  CountdownChip,
  EmptyState,
  PillarChip,
  PlatformDots,
  SkeletonText,
} from "@/components/pasture";
import type { Pillar } from "@/lib/api";
import { formatRemaining, type TimelineItem } from "@/hooks/useDashboardData";
import { DashCard } from "./DashCard";

interface TodayTimelineProps {
  items: TimelineItem[];
  pillars: Pillar[];
  now: Date;
  isLoading?: boolean;
  onToggleHold: (item: TimelineItem) => void;
}

const DOT_CLASS: Record<TimelineItem["kind"], string> = {
  posted: "bg-sage-500",
  review: "bg-cream-500",
  upcoming: "bg-terra-400",
};

function TimelineRow({
  item,
  pillars,
  now,
  onToggleHold,
}: {
  item: TimelineItem;
  pillars: Pillar[];
  now: Date;
  onToggleHold: (item: TimelineItem) => void;
}) {
  const pillarObj = item.pillar
    ? (pillars.find((p) => p.name === item.pillar) ?? item.pillar)
    : null;
  return (
    <div className="relative flex items-start gap-3 py-2.5">
      <div className="t-caption ink-muted w-12 pt-1 text-right font-mono">
        {item.time ?? "—"}
      </div>
      <div className="relative z-[1] shrink-0 pt-1">
        <div
          className={cn("h-3 w-3 rounded-full", DOT_CLASS[item.kind])}
          style={{ boxShadow: "0 0 0 4px var(--surface-card)" }}
          aria-hidden="true"
        />
      </div>
      <div className="min-w-0 flex-1 pl-1">
        <div className="flex items-center gap-2">
          <span className="t-body ink truncate font-medium">{item.title}</span>
          {item.kind === "posted" && <Chip tone="sage">Live</Chip>}
          {item.kind === "review" && <Chip tone="cream">Review</Chip>}
          {item.kind === "upcoming" && <Chip tone="neutral">Queued</Chip>}
        </div>
        <div className="mt-1 flex items-center gap-2">
          <PlatformDots ids={item.platforms} size={12} />
          {pillarObj && <PillarChip pillar={pillarObj} size="xs" />}
          <span className="t-caption ink-muted truncate">· {item.caption}</span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2 pt-0.5">
        {item.autoPublishAt && (
          <CountdownChip
            label={`Releases ${item.time ?? ""}`.trim()}
            remaining={formatRemaining(item.autoPublishAt, now)}
            paused={item.held}
            onToggle={() => onToggleHold(item)}
          />
        )}
        {item.kind === "review" && (
          <Button size="xs" asChild className="fr">
            <Link to="/drafts">
              Review <ArrowRight size={12} strokeWidth={1.75} aria-hidden="true" />
            </Link>
          </Button>
        )}
        {item.kind === "upcoming" && !item.autoPublishAt && (
          <Button size="xs" variant="outline" asChild className="fr">
            <Link to="/calendar">Preview</Link>
          </Button>
        )}
      </div>
    </div>
  );
}

/** "Today's rhythm" — timeline of today's posts, reviews and releases. */
export function TodayTimeline({
  items,
  pillars,
  now,
  isLoading,
  onToggleHold,
}: TodayTimelineProps) {
  return (
    <DashCard
      title={
        <div>
          <h2 className="t-title text-sage-800 dark:text-sage-100">Today's rhythm</h2>
          <div className="t-caption ink-muted mt-0.5">
            {format(now, "EEEE")} · {items.length} {items.length === 1 ? "item" : "items"}
          </div>
        </div>
      }
      right={
        <Button variant="ghost" size="sm" asChild className="fr">
          <Link to="/calendar">
            Full calendar <ArrowRight size={12} strokeWidth={1.75} aria-hidden="true" />
          </Link>
        </Button>
      }
      bodyClassName="pt-1"
    >
      {isLoading ? (
        <SkeletonText lines={4} className="py-3" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Sprout}
          title="A quiet day in the pasture"
          body="Nothing on today's rhythm yet — compose something new."
          action={
            <Button size="sm" asChild className="fr">
              <Link to="/create">Compose</Link>
            </Button>
          }
        />
      ) : (
        <div className="relative">
          <div
            className="absolute top-2 bottom-2 left-[68px] w-px bg-sage-100 dark:bg-sage-700"
            aria-hidden="true"
          />
          {items.map((item) => (
            <TimelineRow
              key={item.id}
              item={item}
              pillars={pillars}
              now={now}
              onToggleHold={onToggleHold}
            />
          ))}
        </div>
      )}
    </DashCard>
  );
}
