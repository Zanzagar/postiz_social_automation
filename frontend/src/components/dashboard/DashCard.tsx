import type * as React from "react";

import { cn } from "@/lib/utils";

interface DashCardProps {
  title?: React.ReactNode;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** Pasture card shell used by dashboard widgets. */
export function DashCard({ title, right, children, className, bodyClassName }: DashCardProps) {
  return (
    <section className={cn("bg-card border-hair rounded-2xl shadow-card", className)}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-2 px-5 pt-4">
          {typeof title === "string" ? (
            <h2 className="t-title text-sage-800 dark:text-sage-100">{title}</h2>
          ) : (
            title
          )}
          {right}
        </header>
      )}
      <div className={cn("px-5 pt-2 pb-4", bodyClassName)}>{children}</div>
    </section>
  );
}
