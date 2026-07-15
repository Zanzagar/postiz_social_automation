import { CHART_GRID, CHART_INK, CHART_PRIOR, CHART_SAGE, shortDate } from "./format";

export interface SeriesPoint {
  date: string;
  value: number;
}

interface AreaChartProps {
  current: SeriesPoint[];
  previous: SeriesPoint[];
  height?: number;
  ariaLabel?: string;
}

const W = 800;
const TIP_W = 110;
const TIP_H = 30;

function polyline(values: number[], max: number, h: number): string {
  if (values.length < 2) return "";
  return values
    .map((v, i) => `${(i / (values.length - 1)) * W},${h - (v / max) * h}`)
    .join(" ");
}

/**
 * Headline engagement-by-day chart: dashed gridlines, prior-period dashed
 * line, filled current-period area, and a peak callout with the real peak
 * date and engagement count. Draws the full per-day series (up to 365 pts).
 */
export function AreaChart({
  current,
  previous,
  height = 240,
  ariaLabel = "Engagement by day, this period compared with the prior period",
}: AreaChartProps) {
  const h = height;
  const vals = current.map((p) => p.value);
  const prevVals = previous.map((p) => p.value);
  if (vals.length < 2) return null;

  const max = Math.max(...vals, ...prevVals, 1);
  const curPath = polyline(vals, max, h);
  const prevPath = polyline(prevVals, max, h);

  const peakValue = Math.max(...vals);
  const peakIdx = vals.indexOf(peakValue);
  const px = (peakIdx / (vals.length - 1)) * W;
  const py = h - (peakValue / max) * h;
  // Keep the tooltip inside the viewBox (peaks near edges or the top).
  const tipX = Math.min(Math.max(px - TIP_W / 2, 4), W - TIP_W - 4);
  const tipY = py - TIP_H - 12 < 4 ? py + 12 : py - TIP_H - 12;

  return (
    <svg
      viewBox={`0 0 ${W} ${h}`}
      className="w-full"
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
    >
      {[0.25, 0.5, 0.75].map((g) => (
        <line
          key={g}
          x1="0"
          x2={W}
          y1={h * g}
          y2={h * g}
          stroke={CHART_GRID}
          strokeDasharray="2 3"
        />
      ))}
      {prevPath && (
        <polyline
          points={prevPath}
          fill="none"
          stroke={CHART_PRIOR}
          strokeWidth="1.5"
          strokeDasharray="3 3"
          vectorEffect="non-scaling-stroke"
        />
      )}
      <polyline
        points={`0,${h} ${curPath} ${W},${h}`}
        fill={CHART_SAGE}
        opacity="0.12"
      />
      <polyline
        points={curPath}
        fill="none"
        stroke={CHART_SAGE}
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
      {peakValue > 0 && (
        <g>
          <circle cx={px} cy={py} r="4" fill="#fff" stroke={CHART_SAGE} strokeWidth="2" />
          <g transform={`translate(${tipX}, ${tipY})`}>
            <rect width={TIP_W} height={TIP_H} rx="6" fill={CHART_INK} />
            <text
              x={TIP_W / 2}
              y="13"
              fontSize="9"
              fill="#fff8e7"
              textAnchor="middle"
              fontWeight="600"
            >
              {shortDate(current[peakIdx].date).toUpperCase()}
            </text>
            <text
              x={TIP_W / 2}
              y="24"
              fontSize="10"
              fill="#fff"
              textAnchor="middle"
              fontFamily="serif"
            >
              {peakValue.toLocaleString()} engagements
            </text>
          </g>
        </g>
      )}
    </svg>
  );
}
