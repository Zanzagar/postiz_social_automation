import { Fragment } from "react";
import {
  Check,
  ChevronRight,
  PenLine,
  Sparkles,
  Sprout,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { CreateStage } from "@/hooks/useLocalDraft";

const STAGES: { id: CreateStage; label: string; sub: string; icon: LucideIcon }[] = [
  { id: "compose", label: "Compose", sub: "Plant the seed", icon: Sprout },
  { id: "generate", label: "Generate", sub: "Let Claude draft", icon: Sparkles },
  { id: "refine", label: "Refine", sub: "Shape each voice", icon: PenLine },
];

interface StageRailProps {
  stage: CreateStage;
  onStage: (stage: CreateStage) => void;
}

/** Compose → Generate → Refine step rail with sage step states. */
export function StageRail({ stage, onStage }: StageRailProps) {
  const idx = STAGES.findIndex((s) => s.id === stage);
  return (
    <div
      className="border-hair-b flex items-stretch gap-2 px-8 py-4"
      style={{
        background: "linear-gradient(to right, var(--surface-warm), var(--surface-card))",
      }}
    >
      {STAGES.map((s, i) => {
        const Ic = s.icon;
        const active = s.id === stage;
        const done = i < idx;
        return (
          <Fragment key={s.id}>
            <button
              type="button"
              onClick={() => onStage(s.id)}
              aria-current={active ? "step" : undefined}
              className={cn(
                "fr flex h-14 flex-1 items-center gap-3 rounded-xl border px-4 text-left transition",
                active
                  ? "bg-card shadow-card border-sage-300 dark:border-sage-600"
                  : done
                    ? "border-sage-200 bg-sage-50/70 dark:border-sage-700 dark:bg-sage-800/60"
                    : "border-hair bg-card opacity-70",
              )}
            >
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                  active
                    ? "bg-sage-500 text-white"
                    : done
                      ? "bg-sage-200 text-sage-700 dark:bg-sage-700 dark:text-sage-100"
                      : "bg-warm ink-muted",
                )}
              >
                {done ? (
                  <Check size={17} strokeWidth={1.75} aria-hidden="true" />
                ) : (
                  <Ic size={17} strokeWidth={1.75} aria-hidden="true" />
                )}
              </div>
              <div>
                <div
                  className={cn(
                    "t-label",
                    active ? "text-sage-600 dark:text-sage-300" : "ink-muted",
                  )}
                >
                  Step {i + 1}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="t-title-sm leading-none font-medium font-serif text-sage-800 dark:text-sage-100">
                    {s.label}
                  </span>
                  <span className="t-caption ink-muted italic">{s.sub}</span>
                </div>
              </div>
            </button>
            {i < STAGES.length - 1 && (
              <div className="ink-muted self-center" aria-hidden="true">
                <ChevronRight size={16} strokeWidth={1.75} />
              </div>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
