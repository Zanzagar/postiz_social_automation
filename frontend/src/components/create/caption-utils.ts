/** Shared caption heuristics for the Create flow. */

export function hashtagCount(caption: string): number {
  return (caption.match(/#\w+/g) ?? []).length;
}

/** Tone note shown when a platform's caption lands (per Pasture design). */
export function toneNote(platformId: string): string {
  switch (platformId) {
    case "linkedin":
      return "measured, professional";
    case "tiktok":
      return "punchy, hook-first";
    case "threads":
      return "conversational";
    default:
      return "warm";
  }
}
