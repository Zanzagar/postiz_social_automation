import type * as React from "react";
import { Sprout, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

/** Centered, calm empty message (drafts, calendar, analytics, media, knowledge). */
export function EmptyState({
  icon: Icon = Sprout,
  title,
  body,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center px-6 py-14 text-center",
        className,
      )}
    >
      <div className="bg-warm border-hair mb-3 flex h-12 w-12 items-center justify-center rounded-2xl text-sage-500 dark:text-sage-300">
        <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <div className="t-title ink font-serif">{title}</div>
      {body && <p className="t-caption ink-muted mt-1 max-w-xs">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
