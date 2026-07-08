/**
 * Pillar display helpers for the Pasture design system.
 *
 * Pillars are DYNAMIC — they come from GET /api/pillars and are managed in
 * Settings. Never treat pillar names as a hardcoded enum. These helpers only
 * provide stable display defaults (color, target %) when the backend has not
 * assigned them.
 */

/** Minimal shape accepted by the helpers — the api `Pillar` type satisfies it. */
export interface PillarLike {
  name: string;
  color?: string | null;
  target?: number | null;
}

/**
 * Default posting-mix targets (percent) by pillar name, per the real content
 * strategy (data.jsx PILLARS). Used only when a pillar has no explicit target.
 */
export const DEFAULT_PILLAR_TARGETS: Record<string, number> = {
  "Cow Life": 40,
  "Farm Ops": 25,
  Community: 15,
  Kitchen: 10,
  Spiritual: 5,
  Support: 5,
  CTA: 5,
};

/** Brand palette (sage / terra / cream family) from data.jsx PILLARS. */
export const PILLAR_PALETTE: string[] = [
  "#4a7c59", // sage-500
  "#b08968", // terra-500
  "#c4a484", // terra-400
  "#e6c46e", // cream-500
  "#5da06e", // sage-400
  "#96704e", // terra-600
];

function hashName(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0;
  }
  return h;
}

function toPillar(pillar: PillarLike | string): PillarLike {
  return typeof pillar === "string" ? { name: pillar } : pillar;
}

/**
 * Display color for a pillar: the backend-assigned color when set, otherwise
 * a stable hash of the name into the brand palette.
 */
export function pillarColor(pillar: PillarLike | string): string {
  const p = toPillar(pillar);
  if (p.color) return p.color;
  const name = p.name ?? "";
  return PILLAR_PALETTE[hashName(name) % PILLAR_PALETTE.length];
}

/**
 * Target posting share (percent) for a pillar: explicit target when set,
 * otherwise the default by name, otherwise null.
 */
export function pillarTarget(pillar: PillarLike | string): number | null {
  const p = toPillar(pillar);
  return p.target ?? DEFAULT_PILLAR_TARGETS[p.name] ?? null;
}
