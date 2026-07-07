import { useState } from "react";

import { PLATFORMS } from "@/lib/platforms";
import { PlatformDot, Toggle } from "@/components/pasture";

/**
 * Connected platforms — display card per supporting.jsx PastureSettings.
 * Toggles are visual only: account connections live in Postiz, not here.
 */
export function PlatformsSection() {
  const [shown, setShown] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(PLATFORMS.map((p) => [p.id, true])),
  );

  return (
    <div className="bg-card border-hair shadow-card max-w-xl rounded-2xl p-4">
      <div className="t-title mb-2 text-sage-800 dark:text-sage-100">
        Connected platforms
      </div>
      <div className="space-y-2">
        {PLATFORMS.map((p) => (
          <div key={p.id} className="flex items-center gap-2">
            <PlatformDot id={p.id} size={14} />
            <span className="t-body ink flex-1">{p.label}</span>
            <span className="t-caption text-sage-600 dark:text-sage-300">
              {p.handle}
            </span>
            <Toggle
              checked={shown[p.id]}
              onChange={(checked) =>
                setShown((prev) => ({ ...prev, [p.id]: checked }))
              }
              aria-label={`Show ${p.label}`}
            />
          </div>
        ))}
      </div>
      <p className="t-micro ink-muted mt-3">
        Account connections are managed in Postiz.
      </p>
    </div>
  );
}
