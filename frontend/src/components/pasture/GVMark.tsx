/** Gita Valley brand mark — stylised wheat sheaf glyph in a circle. */

export type GVMarkTone = "sage" | "cream" | "dark";

interface GVMarkProps {
  size?: number;
  className?: string;
  tone?: GVMarkTone;
}

export function GVMark({ size = 36, className = "", tone = "sage" }: GVMarkProps) {
  const fill =
    tone === "cream" ? "#fff8e7" : tone === "dark" ? "#101a13" : "#4a7c59";
  const stroke = tone === "cream" ? "#4a7c59" : "#ffffff";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      aria-hidden="true"
    >
      <circle cx="32" cy="32" r="30" fill={fill} />
      {/* Wheat sheaf + cow ear arc */}
      <g
        fill="none"
        stroke={stroke}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M32 48V24" />
        <path d="M32 30c-3-2-6-1-8 1 2 2 5 3 8 1zM32 30c3-2 6-1 8 1-2 2-5 3-8 1z" />
        <path d="M32 36c-3-2-6-1-8 1 2 2 5 3 8 1zM32 36c3-2 6-1 8 1-2 2-5 3-8 1z" />
        <path d="M32 24c-2-3 0-6 2-7 1 2 1 5-2 7zM32 24c2-3 0-6-2-7-1 2-1 5 2 7z" />
      </g>
    </svg>
  );
}
