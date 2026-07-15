import { CloudSun } from "lucide-react";

import { EmptyState, SkeletonText } from "@/components/pasture";

/** Composed skeleton shown while a tab's data is on its way in. */
export function TabLoading() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading analytics">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card border-hair shadow-card rounded-xl p-4">
            <SkeletonText lines={2} />
          </div>
        ))}
      </div>
      <div className="bg-card border-hair shadow-card rounded-xl p-5">
        <SkeletonText lines={5} />
      </div>
    </div>
  );
}

/** Quiet degrade for a failed tab fetch — calm copy, no alarms. */
export function TabError() {
  return (
    <EmptyState
      icon={CloudSun}
      title="The results are resting"
      body="We couldn't gather this view just now. Give it a moment and try again."
    />
  );
}
