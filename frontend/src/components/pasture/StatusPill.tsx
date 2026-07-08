import { cn } from "@/lib/utils";
import { STATUS_META } from "./status-meta";

interface StatusPillProps {
  /** Backend status (draft, pending_approval, approved, scheduled, posted, error, template, …) */
  status: string;
  size?: "xs" | "sm";
  className?: string;
}

/** Status pill used in lists — driven by STATUS_META. */
export function StatusPill({ status, size = "sm", className }: StatusPillProps) {
  const m = STATUS_META[status] ?? STATUS_META.draft;
  const sz = size === "xs" ? "t-micro px-1.5" : "t-caption px-2";
  return (
    <span
      className={cn(
        "bg-card border-hair inline-flex items-center gap-1.5 rounded-full py-0.5 font-medium",
        sz,
        m.text,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", m.dot)} aria-hidden="true" />
      {m.label}
    </span>
  );
}
