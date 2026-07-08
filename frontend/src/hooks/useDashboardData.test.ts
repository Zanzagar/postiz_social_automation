import { describe, expect, it } from "vitest";
import type { CalendarEntry, ContentRow, Pillar } from "@/lib/api";
import {
  buildTimeline,
  computePillarBalance,
  computePulseSeries,
  computeStreak,
  formatRemaining,
  platformIds,
} from "./useDashboardData";

// Fixed reference clock — Monday, July 6 2026, 9:00 AM local.
const NOW = new Date("2026-07-06T09:00:00");

function row(overrides: Partial<ContentRow>): ContentRow {
  return {
    row_number: 1,
    date: "2026-07-06",
    content_pillar: "Cow Life",
    raw_text: "Tabby greets the sunrise",
    media_url: null,
    platforms: { instagram: true },
    status: "draft",
    captions: {},
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "manual",
    auto_publish_at: null,
    require_review: false,
    held_at: null,
    alt_text: null,
    ...overrides,
  };
}

function entry(overrides: Partial<CalendarEntry>): CalendarEntry {
  return {
    row_number: 1,
    date: "2026-07-06",
    content_pillar: "Cow Life",
    raw_text: "Tabby greets the sunrise",
    status: "draft",
    platforms: { instagram: true },
    captions: {},
    ...overrides,
  };
}

describe("platformIds", () => {
  it("returns only enabled platforms", () => {
    expect(platformIds({ instagram: true, facebook: false, tiktok: true })).toEqual([
      "instagram",
      "tiktok",
    ]);
  });

  it("handles null input", () => {
    expect(platformIds(null)).toEqual([]);
  });
});

describe("computeStreak", () => {
  it("counts consecutive days ending today", () => {
    const dates = new Set(["2026-07-06", "2026-07-05", "2026-07-04"]);
    expect(computeStreak(dates, NOW)).toBe(3);
  });

  it("allows the streak to survive a quiet morning (counts from yesterday)", () => {
    const dates = new Set(["2026-07-05", "2026-07-04"]);
    expect(computeStreak(dates, NOW)).toBe(2);
  });

  it("returns 0 when the streak is broken", () => {
    const dates = new Set(["2026-07-03"]);
    expect(computeStreak(dates, NOW)).toBe(0);
  });

  it("stops at a gap", () => {
    const dates = new Set(["2026-07-06", "2026-07-04"]);
    expect(computeStreak(dates, NOW)).toBe(1);
  });
});

describe("formatRemaining", () => {
  it("formats hours and minutes", () => {
    expect(formatRemaining("2026-07-06T11:14:00", NOW)).toBe("in 2h 14m");
  });

  it("formats minutes only", () => {
    expect(formatRemaining("2026-07-06T09:08:00", NOW)).toBe("in 8m");
  });

  it("handles past timestamps", () => {
    expect(formatRemaining("2026-07-06T08:00:00", NOW)).toBe("any moment");
  });
});

describe("buildTimeline", () => {
  it("merges today's calendar entries with pending drafts, sorted by time", () => {
    const drafts = [
      row({
        row_number: 10,
        status: "posted",
        posted_at: "2026-07-06T08:15:00",
        raw_text: "Sparkle at morning milking",
      }),
      row({ row_number: 11, raw_text: "Dennis says hello" }),
      row({
        row_number: 12,
        status: "approved",
        auto_publish_at: "2026-07-06T16:30:00",
        raw_text: "The cheese room, late light",
      }),
    ];
    const entries = [
      entry({ row_number: 10, status: "posted", raw_text: "Sparkle at morning milking" }),
      entry({ row_number: 12, status: "approved", raw_text: "The cheese room, late light" }),
      entry({ row_number: 5, status: "posted", date: "2026-07-01", raw_text: "old post" }),
    ];

    const items = buildTimeline(entries, drafts, NOW);
    expect(items.map((i) => i.id)).toEqual([10, 12, 11]);
    expect(items[0]).toMatchObject({ kind: "posted", time: "8:15 AM" });
    expect(items[1]).toMatchObject({
      kind: "upcoming",
      time: "4:30 PM",
      autoPublishAt: "2026-07-06T16:30:00",
      held: false,
    });
    expect(items[2]).toMatchObject({ kind: "review", time: null });
  });

  it("marks held rows and excludes non-today entries", () => {
    const drafts = [
      row({
        row_number: 12,
        status: "approved",
        auto_publish_at: "2026-07-06T16:30:00",
        held_at: "2026-07-06T08:00:00",
      }),
    ];
    const entries = [entry({ row_number: 12, status: "approved" })];
    const items = buildTimeline(entries, drafts, NOW);
    expect(items).toHaveLength(1);
    expect(items[0].held).toBe(true);
    expect(items[0].caption).toBe("held for review");
  });
});

describe("computePillarBalance", () => {
  const pillars: Pillar[] = [
    {
      id: 1,
      name: "Cow Life",
      description: null,
      color: "#4a7c59",
      target: 40,
      is_active: true,
      sort_order: 1,
    },
    {
      id: 2,
      name: "Farm Ops",
      description: null,
      color: null,
      target: null,
      is_active: true,
      sort_order: 2,
    },
  ];

  it("counts last-30-day entries per pillar with pct and target", () => {
    const entries = [
      entry({ row_number: 1, content_pillar: "Cow Life", date: "2026-07-05" }),
      entry({ row_number: 2, content_pillar: "Cow Life", date: "2026-06-20" }),
      entry({ row_number: 3, content_pillar: "Farm Ops", date: "2026-07-01" }),
      // outside the 30-day window
      entry({ row_number: 4, content_pillar: "Cow Life", date: "2026-05-01" }),
    ];
    const rows = computePillarBalance(entries, pillars, NOW);
    const cow = rows.find((r) => r.name === "Cow Life");
    const ops = rows.find((r) => r.name === "Farm Ops");
    expect(cow).toMatchObject({ count: 2, pct: 67, target: 40 });
    // Farm Ops has a default target of 25 by name
    expect(ops).toMatchObject({ count: 1, pct: 33, target: 25 });
  });

  it("includes pillar names found only in calendar data (dynamic pillars)", () => {
    const entries = [
      entry({ row_number: 1, content_pillar: "Bee Keeping", date: "2026-07-05" }),
    ];
    const rows = computePillarBalance(entries, pillars, NOW);
    expect(rows.find((r) => r.name === "Bee Keeping")).toMatchObject({
      count: 1,
      pct: 100,
      target: null,
    });
  });
});

describe("computePulseSeries", () => {
  it("counts posted entries per day, oldest first", () => {
    const entries = [
      entry({ row_number: 1, status: "posted", date: "2026-07-06" }),
      entry({ row_number: 2, status: "posted", date: "2026-07-06" }),
      entry({ row_number: 3, status: "posted", date: "2026-07-05" }),
      entry({ row_number: 4, status: "draft", date: "2026-07-05" }),
    ];
    const series = computePulseSeries(entries, NOW, 3);
    expect(series).toEqual([0, 1, 2]);
  });
});
