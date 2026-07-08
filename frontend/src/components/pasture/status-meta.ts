/**
 * Status pill metadata — ported from design_handoff_pasture/prototype/data.jsx
 * and mapped onto the real backend statuses.
 */

export interface StatusMeta {
  label: string;
  /** Tailwind class for the status dot */
  dot: string;
  /** Tailwind class for the label text */
  text: string;
  /** Tailwind class for a tinted ground (used by calendar cells etc.) */
  bg: string;
}

const NEEDS_REVIEW: StatusMeta = {
  label: "Needs review",
  dot: "bg-cream-500",
  text: "text-cream-ink",
  bg: "bg-cream-100",
};

export const STATUS_META: Record<string, StatusMeta> = {
  posted: {
    label: "Posted",
    dot: "bg-sage-500",
    text: "text-sage-700",
    bg: "bg-sage-50",
  },
  scheduled: {
    label: "Scheduled",
    dot: "bg-sage-300",
    text: "text-sage-700",
    bg: "bg-sage-50",
  },
  approved: {
    label: "Approved",
    dot: "bg-sage-400",
    text: "text-sage-700",
    bg: "bg-sage-50",
  },
  draft: {
    label: "Draft",
    dot: "bg-terra-400",
    text: "text-terra-700",
    bg: "bg-terra-50",
  },
  // Real backend status + prototype alias both resolve to "Needs review".
  pending_approval: NEEDS_REVIEW,
  "needs-review": NEEDS_REVIEW,
  template: {
    label: "Template",
    dot: "bg-terra-300",
    text: "text-terra-700",
    bg: "bg-terra-50",
  },
  error: {
    label: "Error",
    dot: "bg-red-500",
    text: "text-red-700",
    bg: "bg-red-50",
  },
  empty: {
    label: "Empty slot",
    dot: "bg-neutral-300",
    text: "ink-muted",
    bg: "bg-warm",
  },
};
