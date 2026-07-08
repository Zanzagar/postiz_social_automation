import { Link } from "react-router-dom";
import { Leaf } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PlatformDots } from "@/components/pasture";
import { platformIds } from "@/hooks/useDashboardData";
import type { ContentRow } from "@/lib/api";

interface BlessingCardProps {
  pendingDrafts: ContentRow[];
}

/**
 * "Needs your blessing" — inverted sage call-to-action for pending drafts.
 * When nothing is pending, a quiet card takes its place.
 */
export function BlessingCard({ pendingDrafts }: BlessingCardProps) {
  if (pendingDrafts.length === 0) {
    return (
      <section
        data-testid="blessing-quiet"
        className="bg-card border-hair rounded-2xl p-5 shadow-card"
      >
        <div className="t-label ink-muted">Needs your blessing</div>
        <p className="t-body ink-muted mt-2">
          The pasture is quiet — nothing waiting.
        </p>
      </section>
    );
  }

  const first = pendingDrafts[0];
  const ids = platformIds(first.platforms);
  const captionCount = Object.values(first.captions ?? {}).filter(Boolean).length;
  const more = pendingDrafts.length - 1;

  return (
    <section
      data-testid="blessing-card"
      className="relative overflow-hidden rounded-2xl border border-sage-700 bg-sage-800 text-white shadow-card"
    >
      <div className="absolute -right-8 -bottom-8 opacity-[0.08]" aria-hidden="true">
        <Leaf size={180} strokeWidth={1.75} />
      </div>
      <div className="relative p-5">
        <div className="t-label text-sage-200/80">Needs your blessing</div>
        <div className="t-h2 mt-1 leading-tight" style={{ overflowWrap: "anywhere" }}>
          {first.raw_text}
        </div>
        <div className="t-body-sm mt-2 text-sage-100/80">
          {captionCount > 0
            ? `${captionCount} platform caption${captionCount === 1 ? "" : "s"} drafted by Claude.`
            : "Captions not drafted yet."}
          {more > 0 && ` ${more} more draft${more === 1 ? "" : "s"} waiting.`}
        </div>
        {ids.length > 0 && (
          <div className="mt-3 flex items-center gap-1">
            <PlatformDots ids={ids} />
            <span className="t-caption ml-2 text-sage-200/70">
              {ids.length} platform{ids.length === 1 ? "" : "s"}
            </span>
          </div>
        )}
        <div className="mt-4 flex gap-2">
          <Button variant="cream" size="sm" asChild className="fr flex-1">
            <Link to="/drafts">Review captions</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
