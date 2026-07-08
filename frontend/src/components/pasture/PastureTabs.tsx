import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type PastureTabItem =
  | string
  | {
      id: string;
      label?: string;
      icon?: LucideIcon;
    };

export type PastureTabsVariant = "underline" | "pill" | "rail";

interface PastureTabsProps {
  items: PastureTabItem[];
  value: string;
  onChange: (id: string) => void;
  variant?: PastureTabsVariant;
  className?: string;
  "aria-label"?: string;
}

function itemId(it: PastureTabItem): string {
  return typeof it === "string" ? it : it.id;
}

function itemLabel(it: PastureTabItem): string {
  return typeof it === "string" ? it : (it.label ?? it.id);
}

/**
 * Tabs — consolidates the Analytics / Knowledge / Settings tab strips.
 * variants: underline (Analytics) · pill (Knowledge filters) · rail (Settings, vertical).
 * a11y: role=tablist/tab, aria-selected, arrow-key roving tabindex.
 */
export function PastureTabs({
  items,
  value,
  onChange,
  variant = "underline",
  className,
  "aria-label": ariaLabel,
}: PastureTabsProps) {
  const vertical = variant === "rail";
  const refs = React.useRef<Array<HTMLButtonElement | null>>([]);

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    const nextKey = vertical ? "ArrowDown" : "ArrowRight";
    const prevKey = vertical ? "ArrowUp" : "ArrowLeft";
    let next: number | null = null;
    if (e.key === nextKey) next = (index + 1) % items.length;
    else if (e.key === prevKey) next = (index - 1 + items.length) % items.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = items.length - 1;
    if (next === null) return;
    e.preventDefault();
    refs.current[next]?.focus();
    onChange(itemId(items[next]));
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      aria-orientation={vertical ? "vertical" : "horizontal"}
      className={cn(
        vertical ? "flex flex-col gap-0.5" : "flex items-center gap-1",
        className,
      )}
    >
      {items.map((it, i) => {
        const id = itemId(it);
        const active = id === value;
        const IconComp = typeof it === "string" ? undefined : it.icon;
        const base = "fr rounded-lg t-ui font-medium transition-colors";
        const styles =
          variant === "underline"
            ? cn(
                "-mb-px rounded-none border-b-2 px-1 py-2",
                active
                  ? "border-sage-500 text-sage-800 dark:text-sage-100"
                  : "ink-muted border-transparent hover:text-sage-700 dark:hover:text-sage-300",
              )
            : variant === "pill"
              ? cn(
                  "h-8 px-3",
                  active
                    ? "bg-sage-500 text-white"
                    : "bg-card border-hair ink-muted hover:text-sage-700 dark:hover:text-sage-300",
                )
              : cn(
                  "flex h-9 items-center gap-2 px-3 text-left",
                  active
                    ? "bg-sage-500 text-white"
                    : "ink-muted hover:bg-sage-50 dark:hover:bg-sage-800",
                );
        return (
          <button
            key={id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(id)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            className={cn(base, styles)}
          >
            {IconComp && <IconComp size={15} strokeWidth={1.75} aria-hidden="true" />}
            {itemLabel(it)}
          </button>
        );
      })}
    </div>
  );
}
