import { ACCENT_COLORS, type AccentTone } from "./format";

interface SparkProps {
  series: number[];
  accent?: AccentTone;
  /** Accessible description; omit to mark the spark decorative. */
  ariaLabel?: string;
}

/** Tiny polyline sparkline with a soft area fill (KPI cards). */
export function Spark({ series, accent = "sage", ariaLabel }: SparkProps) {
  if (series.length < 2) return null;
  const color = ACCENT_COLORS[accent];
  const w = 100;
  const h = 32;
  const max = Math.max(...series, 1);
  const pts = series
    .map((v, i) => `${(i / (series.length - 1)) * w},${h - (v / max) * h}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-2 h-8 w-full"
      preserveAspectRatio="none"
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
      aria-hidden={ariaLabel ? undefined : true}
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color} opacity="0.1" />
    </svg>
  );
}
