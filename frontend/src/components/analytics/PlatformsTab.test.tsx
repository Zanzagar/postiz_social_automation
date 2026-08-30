import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AnalyticsHeatmap, PlatformStatRow } from "@/lib/api";
import { PlatformsTab } from "./PlatformsTab";

const HEATMAP: AnalyticsHeatmap = {
  days: [
    [0, 1],
    [2, 3],
    [1, 0],
    [0, 0],
    [1, 1],
    [0, 2],
    [3, 1],
  ],
  hour_buckets: ["6a", "9a"],
  peak: { day: 1, bucket: 1 },
  sample_size: 22,
};

function renderTab(platforms: PlatformStatRow[]) {
  return render(
    <PlatformsTab
      platforms={platforms}
      heatmap={HEATMAP}
      isLoading={false}
      isError={false}
      range="30d"
    />,
  );
}

function reachRow(): HTMLElement {
  const row = screen.getByText("Reach").parentElement;
  expect(row).not.toBeNull();
  return row!;
}

describe("PlatformsTab honest reach", () => {
  it("renders an em dash instead of 'Reach 0' when reach was never imported", () => {
    renderTab([
      { platform: "facebook", posts: 8, engagement: 1200, reach: 0, rate: null },
    ]);

    // matches the Overview tile — 0 means "not imported", never "nobody reached"
    expect(within(reachRow()).getByText("—")).toBeInTheDocument();
    expect(within(reachRow()).queryByText("0")).not.toBeInTheDocument();
  });

  it("keeps real reach numbers untouched", () => {
    renderTab([
      { platform: "instagram", posts: 14, engagement: 4300, reach: 48200, rate: 9.1 },
    ]);

    expect(within(reachRow()).getByText("48,200")).toBeInTheDocument();
  });
});
