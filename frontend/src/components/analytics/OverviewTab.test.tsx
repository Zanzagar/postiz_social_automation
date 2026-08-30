import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AnalyticsSummary } from "@/lib/api";
import { OverviewTab } from "./OverviewTab";

function summary(overrides: Partial<AnalyticsSummary> = {}): AnalyticsSummary {
  return {
    range: "30d",
    kpis: {
      posts: { value: 34, delta_pct: 6, series: [4, 6, 5, 8] },
      engagement: { value: 18200, delta_pct: 27, series: [2, 3, 5, 8] },
      avg_rate: { value: 4.8, delta_pct: null, series: [3, 4, 5, 5] },
      reach: { value: 48200, delta_pct: 12, series: [1, 2, 3, 5] },
    },
    engagement_by_day: {
      current: [
        { date: "2026-07-01", value: 10 },
        { date: "2026-07-02", value: 40 },
        { date: "2026-07-03", value: 22 },
      ],
      previous: [
        { date: "2026-06-01", value: 8 },
        { date: "2026-06-02", value: 12 },
        { date: "2026-06-03", value: 20 },
      ],
    },
    top_post: null,
    insights: [],
    sources: { app: 20, history: 0 },
    ...overrides,
  };
}

function renderTab(data: AnalyticsSummary, range = "30d") {
  return render(
    <OverviewTab data={data} isLoading={false} isError={false} range={range} />,
  );
}

function kpiCard(label: string): HTMLElement {
  const card = screen.getByText(label).parentElement;
  expect(card).not.toBeNull();
  return card!;
}

describe("OverviewTab all-time honesty", () => {
  it("hides the prior-period legend and aria claim at range 'all' (no prior series exists)", () => {
    renderTab(
      summary({ engagement_by_day: { current: summary().engagement_by_day.current, previous: [] } }),
      "all",
    );

    expect(screen.queryByText(/^Prior /)).not.toBeInTheDocument();
    const chart = screen.getByRole("img", { name: /engagement by day/i });
    expect(chart.getAttribute("aria-label")).not.toMatch(/prior/i);
  });

  it("keeps the prior legend and aria comparison on bounded ranges", () => {
    renderTab(summary(), "30d");

    expect(screen.getByText("Prior 30 days")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: /this period compared with the prior period/i,
      }),
    ).toBeInTheDocument();
  });
});

describe("OverviewTab honest KPI tiles", () => {
  it("renders an em dash for Avg. engagement rate when the rate is null", () => {
    const data = summary();
    data.kpis.avg_rate = { value: null, delta_pct: null, series: [] };
    renderTab(data);

    expect(within(kpiCard("Avg. engagement rate")).getByText("—")).toBeInTheDocument();
  });

  it("explains the missing rate with a tooltip, like the reach tile", () => {
    const data = summary();
    data.kpis.avg_rate = { value: null, delta_pct: null, series: [] };
    renderTab(data);

    const rateTile = screen.getByTitle("Needs reach data to compute");
    expect(within(rateTile).getByText("Avg. engagement rate")).toBeInTheDocument();
    expect(within(rateTile).getByText("—")).toBeInTheDocument();
  });

  it("renders — with an explanatory title for Total reach when reach is 0", () => {
    const data = summary();
    data.kpis.reach = { value: 0, delta_pct: null, series: [] };
    renderTab(data);

    const reachTile = screen.getByTitle("No reach data imported yet");
    expect(within(reachTile).getByText("Total reach")).toBeInTheDocument();
    expect(within(reachTile).getByText("—")).toBeInTheDocument();
  });

  it("keeps real reach and rate values untouched", () => {
    renderTab(summary());

    expect(within(kpiCard("Total reach")).getByText("48.2k")).toBeInTheDocument();
    expect(within(kpiCard("Avg. engagement rate")).getByText("4.8%")).toBeInTheDocument();
    expect(screen.queryByTitle("No reach data imported yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTitle("Needs reach data to compute"),
    ).not.toBeInTheDocument();
  });
});
