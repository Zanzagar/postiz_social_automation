import { TrendingUp } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/pasture";

/**
 * Results (analytics) page — Phase 2 stub.
 * Replaced wholesale next wave by the full analytics build.
 */
export function AnalyticsPage() {
  return (
    <div>
      <PageHeader
        greeting="Analytics"
        title="Results"
        subtitle="How your pasture fed the feed."
        icon={TrendingUp}
      />
      <EmptyState
        icon={TrendingUp}
        title="Analytics are growing in"
        body="Once your posts have been out in the field a little while, their results will take root here."
      />
    </div>
  );
}
