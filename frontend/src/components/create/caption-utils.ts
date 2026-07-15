/** Shared caption heuristics for the Create flow. */

export function hashtagCount(caption: string): number {
  return (caption.match(/#\w+/g) ?? []).length;
}

/** Strip any leading "#" so tags from the API can be safely re-prefixed. */
export function bareHashtag(tag: string): string {
  return tag.replace(/^#+/, "");
}

/**
 * Case-insensitive whole-tag check: does the caption already hold "#tag"?
 * Word-boundary aware so "#cowsofinstagram" doesn't hide the separate "#cows"
 * suggestion (and vice versa).
 */
export function captionHasHashtag(caption: string, tag: string): boolean {
  const escaped = bareHashtag(tag).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`#${escaped}(?![\\w])`, "i").test(caption);
}

/** Append " #tag" to a caption (no leading space when the caption is empty). */
export function appendHashtag(caption: string, tag: string): string {
  const withHash = `#${bareHashtag(tag)}`;
  return caption ? `${caption} ${withHash}` : withHash;
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
