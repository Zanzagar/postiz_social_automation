import { describe, expect, it } from "vitest";
import type { AnalyticsPostRow } from "@/lib/api";
import {
  buildResultsCsv,
  compactNumber,
  formatDelta,
  formatRate,
  rangeMeta,
  shortDate,
} from "./format";

describe("analytics format helpers", () => {
  it("compacts large numbers", () => {
    expect(compactNumber(340)).toBe("340");
    expect(compactNumber(18200)).toBe("18.2k");
    expect(compactNumber(48000)).toBe("48k");
    expect(compactNumber(1_250_000)).toBe("1.3m");
  });

  it("formats rates and honest placeholders", () => {
    expect(formatRate(4.8)).toBe("4.8%");
    expect(formatRate(12)).toBe("12%");
    expect(formatRate(null)).toBe("—");
  });

  it("formats signed deltas and omits unknowable ones", () => {
    expect(formatDelta(27)).toBe("+27%");
    expect(formatDelta(-3.5)).toBe("-3.5%");
    expect(formatDelta(null)).toBeNull();
  });

  it("parses date-only strings without UTC day shift", () => {
    expect(shortDate("2026-03-08")).toMatch(/Mar 8/);
    expect(shortDate("not-a-date")).toBe("not-a-date");
  });

  it("maps ranges to labels with a 30d fallback", () => {
    expect(rangeMeta("7d").noun).toBe("week");
    expect(rangeMeta("365d").label).toBe("Year");
    expect(rangeMeta("bogus").noun).toBe("month");
  });

  it("builds a CSV with escaped fields and honest blanks", () => {
    const rows: AnalyticsPostRow[] = [
      {
        id: 1,
        source: "app",
        title: 'Lakshmi says "moo"',
        pillar: "Cow Life",
        platforms: ["instagram", "facebook"],
        date: "2026-07-03",
        engagement: 3442,
        rate: 12.1,
        trend: "up",
      },
      {
        id: null,
        source: "history",
        title: "Old post",
        pillar: null,
        platforms: ["facebook"],
        date: "2026-07-01",
        engagement: 12,
        rate: null,
        trend: "flat",
      },
    ];
    const csv = buildResultsCsv(rows);
    const lines = csv.split("\n");
    expect(lines[0]).toBe("Title,Pillar,Platforms,Date,Engagement,Rate,Trend,Source");
    expect(lines[1]).toBe(
      '"Lakshmi says ""moo""","Cow Life","instagram|facebook","2026-07-03",3442,12.1,up,app',
    );
    expect(lines[2]).toBe('"Old post","","facebook","2026-07-01",12,,flat,history');
  });
});
