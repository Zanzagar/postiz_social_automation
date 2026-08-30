import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RhythmWeek, SeasonSummary } from "@/lib/api";
import { RhythmTab } from "./RhythmTab";

// Frozen "today" — Tuesday, July 14 2026. The cadence card anchors its
// monthly buckets on the Monday of the current week (Jul 13 2026).
const TODAY = new Date("2026-07-14T09:00:00");

const SEASON: SeasonSummary = {
  total_posts: 13,
  consistency: { on_target_weeks: 3, total_weeks: 4 },
  best_slot: { day: "Tuesday", hour_bucket: "9a" },
  avg_lead_days: 3.4,
};

/** n consecutive Monday-start weeks ending with the current week. */
function makeWeeks(n: number, overrides: Partial<RhythmWeek> = {}): RhythmWeek[] {
  return Array.from({ length: n }, (_, i) => ({
    label: `Week ${i + 1}`,
    posted: 1,
    target: null,
    ...overrides,
  }));
}

function renderTab(weeks: RhythmWeek[]) {
  return render(
    <RhythmTab
      weeks={weeks}
      festivals={[]}
      season={SEASON}
      isLoading={false}
      isError={false}
      range="all"
    />,
  );
}

/** The cadence bar row containing the given label. */
function cadenceRow(label: string): HTMLElement {
  const row = screen.getByText(label).parentElement;
  expect(row).not.toBeNull();
  return row!;
}

describe("RhythmTab cadence aggregation", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(TODAY);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders every week unchanged at 30 weeks or fewer", () => {
    renderTab(makeWeeks(30));

    expect(screen.getByText("Week 1")).toBeInTheDocument();
    expect(screen.getByText("Week 30")).toBeInTheDocument();
    expect(screen.getByText(/week-by-week/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/shown monthly across the full history/i),
    ).not.toBeInTheDocument();
  });

  it("collapses more than 30 weeks into calendar-month buckets", () => {
    renderTab(makeWeeks(31));

    // 31 Monday-start weeks ending Jul 13 2026 begin Dec 15 2025:
    // Dec 2025 holds 3 of them, Jul 2026 the final 2.
    expect(screen.queryByText("Week 1")).not.toBeInTheDocument();
    expect(within(cadenceRow("Dec 2025")).getByText("3")).toBeInTheDocument();
    expect(within(cadenceRow("Jul 2026")).getByText("2")).toBeInTheDocument();
    expect(screen.getByText(/month-by-month/i)).toBeInTheDocument();
    expect(
      screen.getByText(/shown monthly across the full history/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/week-by-week/i)).not.toBeInTheDocument();
  });

  it("sums weekly targets into the monthly buckets", () => {
    renderTab(makeWeeks(31, { target: 2 }));

    expect(within(cadenceRow("Dec 2025")).getByText("3/6")).toBeInTheDocument();
    expect(within(cadenceRow("Jul 2026")).getByText("2/4")).toBeInTheDocument();
    expect(screen.getByText("Monthly target")).toBeInTheDocument();
    expect(screen.queryByText("Weekly target")).not.toBeInTheDocument();
  });

  it("keeps the season consistency line reading from props.season", () => {
    renderTab(makeWeeks(31));

    expect(screen.getByText("3 of 4 weeks on target")).toBeInTheDocument();
  });
});
