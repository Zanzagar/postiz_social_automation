import { describe, expect, it } from "vitest";

import { appendHashtag, bareHashtag, captionHasHashtag, hashtagCount } from "./caption-utils";

describe("captionHasHashtag", () => {
  it("finds an exact tag regardless of case", () => {
    expect(captionHasHashtag("Morning walk #FarmLife", "farmlife")).toBe(true);
    expect(captionHasHashtag("Morning walk #farmlife", "#FarmLife")).toBe(true);
  });

  it("does NOT treat #cowsofinstagram as containing #cows (regression: substring hide)", () => {
    expect(captionHasHashtag("Meet the herd #cowsofinstagram", "cows")).toBe(false);
  });

  it("does NOT treat #cows as containing #cowsofinstagram", () => {
    expect(captionHasHashtag("Meet the herd #cows", "cowsofinstagram")).toBe(false);
  });

  it("still matches the tag at word boundaries (end, punctuation, mid-caption)", () => {
    expect(captionHasHashtag("Meet the herd #cows", "cows")).toBe(true);
    expect(captionHasHashtag("Meet the herd #cows!", "cows")).toBe(true);
    expect(captionHasHashtag("#cows grazing at dusk", "cows")).toBe(true);
  });

  it("returns false when the tag is absent", () => {
    expect(captionHasHashtag("Quiet morning at the barn", "cows")).toBe(false);
  });
});

describe("bareHashtag / appendHashtag / hashtagCount", () => {
  it("strips leading hashes", () => {
    expect(bareHashtag("##cows")).toBe("cows");
    expect(bareHashtag("cows")).toBe("cows");
  });

  it("appends with a single space, none when empty", () => {
    expect(appendHashtag("Hello", "cows")).toBe("Hello #cows");
    expect(appendHashtag("", "#cows")).toBe("#cows");
  });

  it("counts hashtags", () => {
    expect(hashtagCount("a #b c #d")).toBe(2);
    expect(hashtagCount("none here")).toBe(0);
  });
});
