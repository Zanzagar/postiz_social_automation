import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DRAFT_STORAGE_KEY,
  useLocalDraft,
  type CreateDraft,
} from "./useLocalDraft";

function storedDraft(): Partial<CreateDraft> | null {
  const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
  return raw ? (JSON.parse(raw) as Partial<CreateDraft>) : null;
}

describe("useLocalDraft", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with an empty compose draft when nothing is stored", () => {
    const { result } = renderHook(() => useLocalDraft());
    expect(result.current.draft.seed).toBe("");
    expect(result.current.draft.platforms).toEqual([]);
    expect(result.current.draft.stage).toBe("compose");
    expect(result.current.draft.rowId).toBeNull();
  });

  it("persists updates to localStorage after the debounce delay", () => {
    const { result } = renderHook(() => useLocalDraft());

    act(() => {
      result.current.update({ seed: "Tabby met the herd", platforms: ["instagram"] });
    });

    // Not written synchronously (debounced)
    expect(storedDraft()).toBeNull();

    act(() => {
      vi.advanceTimersByTime(500);
    });

    const stored = storedDraft();
    expect(stored?.seed).toBe("Tabby met the herd");
    expect(stored?.platforms).toEqual(["instagram"]);
  });

  it("restores a stored draft on mount", () => {
    localStorage.setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify({
        seed: "Sparkle greeted the visitors",
        platforms: ["instagram", "threads"],
        pillar: "Cow Life",
        altText: "Sparkle the cow in the pasture",
        stage: "compose",
      }),
    );

    const { result } = renderHook(() => useLocalDraft());
    expect(result.current.draft.seed).toBe("Sparkle greeted the visitors");
    expect(result.current.draft.platforms).toEqual(["instagram", "threads"]);
    expect(result.current.draft.pillar).toBe("Cow Life");
    expect(result.current.draft.altText).toBe("Sparkle the cow in the pasture");
  });

  it("never restores into the generate stage", () => {
    localStorage.setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify({ seed: "Dennis in the barn", stage: "generate" }),
    );
    const { result } = renderHook(() => useLocalDraft());
    expect(result.current.draft.stage).toBe("compose");
  });

  it("falls back to compose when restoring refine with no captions", () => {
    localStorage.setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify({ seed: "Brisham update", stage: "refine", captions: {} }),
    );
    const { result } = renderHook(() => useLocalDraft());
    expect(result.current.draft.stage).toBe("compose");
  });

  it("clear() removes the stored draft and resets state", () => {
    const { result } = renderHook(() => useLocalDraft());

    act(() => {
      result.current.update({ seed: "Daring Denise escaped again" });
    });
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(storedDraft()?.seed).toBe("Daring Denise escaped again");

    act(() => {
      result.current.clear();
    });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(storedDraft()).toBeNull();
    expect(result.current.draft.seed).toBe("");
  });

  it("survives malformed stored JSON", () => {
    localStorage.setItem(DRAFT_STORAGE_KEY, "{not json");
    const { result } = renderHook(() => useLocalDraft());
    expect(result.current.draft.stage).toBe("compose");
  });
});
