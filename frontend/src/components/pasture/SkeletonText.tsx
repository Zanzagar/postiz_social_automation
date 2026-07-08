import type * as React from "react";

import { cn } from "@/lib/utils";

interface SkeletonBarProps {
  w?: number | string;
  h?: number | string;
  radius?: number | string;
  className?: string;
  style?: React.CSSProperties;
}

function SkeletonBar({ w = "100%", h = 12, radius, className, style }: SkeletonBarProps) {
  return (
    <div
      className={cn("skeleton", className)}
      style={{ width: w, height: h, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

/** Shimmering text placeholder — the last line is shortened to 60%. */
export function SkeletonText({ lines = 3, className }: SkeletonTextProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBar key={i} h={10} w={i === lines - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
}
