/**
 * Static platform data for the Pasture design system.
 * Ported from design_handoff_pasture/prototype/data.jsx — keep in sync.
 */

export type PlatformId =
  | "instagram"
  | "facebook"
  | "tiktok"
  | "threads"
  | "linkedin";

export interface Platform {
  id: PlatformId;
  label: string;
  color: string;
  /** Hard caption character limit */
  max: number;
  /** Ideal caption length */
  ideal: number;
  handle: string;
  hashMin: number;
  hashMax: number;
  /** CSS background for the platform dot */
  gradient: string;
}

export const PLATFORMS: Platform[] = [
  {
    id: "instagram",
    label: "Instagram",
    color: "#E4405F",
    max: 2200,
    ideal: 150,
    handle: "gita.valley",
    hashMin: 5,
    hashMax: 30,
    gradient:
      "linear-gradient(135deg,#feda75,#fa7e1e,#d62976,#962fbf,#4f5bd5)",
  },
  {
    id: "facebook",
    label: "Facebook",
    color: "#1877F2",
    max: 63206,
    ideal: 280,
    handle: "Gita Valley",
    hashMin: 3,
    hashMax: 5,
    gradient: "#1877F2",
  },
  {
    id: "tiktok",
    label: "TikTok",
    color: "#000000",
    max: 2200,
    ideal: 100,
    handle: "@gitavalley",
    hashMin: 3,
    hashMax: 5,
    gradient: "#000000",
  },
  {
    id: "threads",
    label: "Threads",
    color: "#000000",
    max: 500,
    ideal: 120,
    handle: "@gita.valley",
    hashMin: 0,
    hashMax: 0,
    gradient: "#000000",
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    color: "#0A66C2",
    max: 3000,
    ideal: 220,
    handle: "Gita Valley",
    hashMin: 3,
    hashMax: 5,
    gradient: "#0A66C2",
  },
];

export function platformBy(id: string): Platform {
  return PLATFORMS.find((p) => p.id === id) ?? PLATFORMS[0];
}
