import { useState } from "react";

import { Toggle } from "@/components/pasture";

const RELEASE_STEPS: ReadonlyArray<[string, string]> = [
  ["Approve", "A post is blessed — by you, or auto-approved where allowed."],
  [
    "Rest",
    "It waits out the platform's rest window. The countdown is visible everywhere the post appears.",
  ],
  [
    "Release",
    "It publishes through Postiz. A toast confirms, with a link to see it live.",
  ],
];

/**
 * Right column of the Publishing section — "How release works" explainer
 * and the per-post override demo (phase1.jsx PastureAutoPublish).
 *
 * The prototype's "This week" stat card is intentionally omitted: released/held
 * counts are not derivable from the calendar API, and we never fake numbers.
 */
export function PublishingAside() {
  const [requireReview, setRequireReview] = useState(true);
  return (
    <div className="space-y-5">
      <div
        className="text-cream-100 rounded-2xl p-5"
        style={{ background: "linear-gradient(160deg, #2d4a35, #1e3224)" }}
      >
        <div className="t-label text-cream-300 mb-3">How release works</div>
        <ol className="space-y-3">
          {RELEASE_STEPS.map(([title, sub], i) => (
            <li key={title} className="flex gap-3">
              <span className="bg-cream-400/20 text-cream-200 t-micro flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-semibold">
                {i + 1}
              </span>
              <div>
                <div className="t-body-sm text-cream-100 font-semibold">{title}</div>
                <div className="t-caption text-cream-200/80">{sub}</div>
              </div>
            </li>
          ))}
        </ol>
        <div
          className="t-micro text-cream-300/70 mt-4 pt-3"
          style={{ borderTop: "1px solid rgba(255,240,201,.15)" }}
        >
          Pausing any countdown holds the post for review. Nothing releases while
          held.
        </div>
      </div>

      <div className="bg-card border-hair shadow-card rounded-2xl p-4">
        <div className="t-title-sm ink mb-2.5 font-semibold">Per-post override</div>
        <div className="bg-warm flex h-11 items-center justify-between gap-3 rounded-lg px-3">
          <span className="t-body-sm ink">Require review for this post</span>
          <Toggle
            size="sm"
            checked={requireReview}
            onChange={setRequireReview}
            aria-label="Require review for this post"
          />
        </div>
        <p className="t-micro ink-muted mt-2">
          Any single post can insist on a blessing, regardless of the rules above.
          Lives in the editor.
        </p>
      </div>
    </div>
  );
}
