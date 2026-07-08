import type * as React from "react";

import { platformBy } from "@/lib/platforms";

/* Inline platform glyphs (from primitives.jsx) — decorative, aria-hidden. */

function InstaGlyph({ size = 10 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="#fff"
      strokeWidth="2"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1" fill="#fff" />
    </svg>
  );
}

function TikTokGlyph({ size = 10 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#fff" aria-hidden="true">
      <path d="M12 2h3c.3 2 1.7 3.7 3.7 4v3c-1.3 0-2.6-.3-3.7-1v7a5 5 0 1 1-5-5v3a2 2 0 1 0 2 2V2z" />
    </svg>
  );
}

function ThreadsGlyph({ size = 10 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="#fff"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M12 3c5 0 8 3 8 9s-3 9-8 9c-4 0-6-2-6-5 0-2.5 2-4 4.5-4 2 0 3 1 3 2.5 0 2-1.5 3-3 3M8 8c1-2 2-3 4-3 3 0 5 2 5 5" />
    </svg>
  );
}

interface PlatformDotProps {
  id: string;
  size?: number;
  z?: number;
}

/**
 * Brand-gradient circle with the platform glyph. Decorative — the accessible
 * platform name lives on the adjacent chip/label, not the dot.
 */
export function PlatformDot({ id, size = 14, z = 1 }: PlatformDotProps) {
  const p = platformBy(id);
  const glyph: Record<string, React.ReactNode> = {
    instagram: <InstaGlyph size={size * 0.6} />,
    facebook: (
      <span style={{ fontSize: size * 0.6, fontWeight: 700, color: "#fff" }} aria-hidden="true">
        f
      </span>
    ),
    tiktok: <TikTokGlyph size={size * 0.6} />,
    threads: <ThreadsGlyph size={size * 0.6} />,
    linkedin: (
      <span
        style={{ fontSize: size * 0.55, fontWeight: 700, color: "#fff", letterSpacing: -1 }}
        aria-hidden="true"
      >
        in
      </span>
    ),
  };
  return (
    <span
      style={{
        width: size * 1.6,
        height: size * 1.6,
        background: p.gradient,
        zIndex: z,
        // ring-2 equivalent — ring color must follow the card surface, not white
        boxShadow: "0 0 0 2px var(--surface-card)",
      }}
      className="inline-flex items-center justify-center rounded-full"
      aria-hidden="true"
    >
      {glyph[p.id]}
    </span>
  );
}

interface PlatformDotsProps {
  ids: string[];
  size?: number;
}

/** Overlapping row of platform dots (caps at the 5-platform set). */
export function PlatformDots({ ids, size = 14 }: PlatformDotsProps) {
  return (
    <div className="flex -space-x-1.5">
      {ids.map((id, i) => (
        <PlatformDot key={id} id={id} size={size} z={ids.length - i} />
      ))}
    </div>
  );
}
