import type * as React from "react";
import { Sunrise, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  subtitle?: React.ReactNode;
  /** Right-aligned actions */
  right?: React.ReactNode;
  /** lucide-react icon component for the 40px icon box */
  icon?: LucideIcon;
  /** Uppercase kicker line above the title */
  greeting?: string;
  className?: string;
}

/**
 * Page header (the PastureTopbar spec, canonical name PageHeader):
 * 40px rounded-xl sage-50 icon box, serif 28px title, optional greeting
 * kicker, subtitle, and right-aligned actions.
 */
export function PageHeader({
  title,
  subtitle,
  right,
  icon: Icon = Sunrise,
  greeting,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "border-hair-b flex items-start justify-between px-8 pt-7 pb-4",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-sage-100 bg-sage-50 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-200">
          <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
        </div>
        <div>
          {greeting && (
            <div className="t-body-sm mb-0.5 font-medium tracking-wider text-sage-700/70 uppercase dark:text-sage-300/70">
              {greeting}
            </div>
          )}
          <h1 className="t-h1 font-medium text-sage-800 dark:text-sage-100">{title}</h1>
          {subtitle && <p className="t-body ink-muted mt-0.5 max-w-2xl">{subtitle}</p>}
        </div>
      </div>
      {right && <div className="flex items-center gap-2 pt-1">{right}</div>}
    </div>
  );
}
