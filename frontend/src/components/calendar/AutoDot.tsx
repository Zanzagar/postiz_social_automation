/**
 * Quiet "auto" clock dot — phase1.jsx StateCard 2. Shown on calendar
 * surfaces for rows with auto_publish_at; no countdown noise at this zoom.
 */
export function AutoDot() {
  return (
    <span
      className="flex items-center gap-1 text-sage-700 dark:text-sage-300"
      title="Auto-publishes — open to see the countdown"
    >
      <svg
        width="9"
        height="9"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </svg>
      <span className="t-micro font-semibold">auto</span>
    </span>
  );
}
