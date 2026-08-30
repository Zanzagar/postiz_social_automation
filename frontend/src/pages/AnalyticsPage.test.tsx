import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { AnalyticsPage } from "./AnalyticsPage";
import type { AnalyticsPostRow, AnalyticsSummary } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getAnalyticsSummary: vi.fn(),
    getAnalyticsPosts: vi.fn(),
    getAnalyticsPillarInsights: vi.fn(),
    getAnalyticsPlatforms: vi.fn(),
    getAnalyticsRhythm: vi.fn(),
  },
  ApiError: class extends Error {
    status: number;
    detail: string;
    constructor(s: number, d: string) {
      super(d);
      this.status = s;
      this.detail = d;
    }
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { api } from "@/lib/api";

const mockSummary = vi.mocked(api.getAnalyticsSummary);
const mockPosts = vi.mocked(api.getAnalyticsPosts);
const mockPillars = vi.mocked(api.getAnalyticsPillarInsights);
const mockPlatforms = vi.mocked(api.getAnalyticsPlatforms);
const mockRhythm = vi.mocked(api.getAnalyticsRhythm);

// Frozen "today" — Tuesday, July 14 2026, 9:00 AM local time.
const TODAY = new Date("2026-07-14T09:00:00");

const SUMMARY: AnalyticsSummary = {
  range: "30d",
  kpis: {
    posts: { value: 34, delta_pct: 6, series: [4, 6, 5, 8, 7, 9, 11] },
    engagement: { value: 18200, delta_pct: 27, series: [2, 3, 3, 5, 4, 6, 8] },
    avg_rate: { value: 4.8, delta_pct: null, series: [3, 4, 4, 4, 5, 5, 5] },
    reach: { value: 48200, delta_pct: 12, series: [1, 2, 2, 3, 3, 4, 5] },
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
  top_post: {
    id: 5,
    source: "app",
    title: "Lakshmi and her calf — first morning",
    platform: "instagram",
    date: "2026-07-03",
    pillar: "Cow Life",
    likes: 3400,
    comments: 287,
    engagement: 3442,
    rate: 12.1,
  },
  insights: [
    { tone: "sage", title: "Herd posts outperform", body: "The herd earns more love." },
  ],
  sources: { app: 20, history: 14 },
};

const EMPTY_SUMMARY: AnalyticsSummary = {
  range: "30d",
  kpis: {
    posts: { value: 0, delta_pct: null, series: [] },
    engagement: { value: 0, delta_pct: null, series: [] },
    avg_rate: { value: 0, delta_pct: null, series: [] },
    reach: { value: 0, delta_pct: null, series: [] },
  },
  engagement_by_day: { current: [], previous: [] },
  top_post: null,
  insights: [],
  sources: { app: 0, history: 0 },
};

const POST_ROWS: AnalyticsPostRow[] = [
  {
    id: 1,
    source: "app",
    title: "Lakshmi and her calf",
    pillar: "Cow Life",
    platforms: ["instagram"],
    date: "2026-07-03",
    engagement: 3442,
    rate: 12.1,
    trend: "up",
  },
  {
    id: null,
    source: "history",
    title: "Morning milking in the fog",
    pillar: null,
    platforms: ["facebook"],
    date: "2026-07-01",
    engagement: 980,
    rate: null,
    trend: "flat",
  },
  {
    id: 3,
    source: "app",
    title: "Sponsor a cow",
    pillar: "Support",
    platforms: ["facebook", "instagram"],
    date: "2026-06-28",
    engagement: 412,
    rate: 1.2,
    trend: "down",
  },
];

const PILLAR_DATA = {
  pillars: [
    {
      pillar: "Cow Life",
      color: "#4a7c59",
      posts: 14,
      engagement: 7420,
      rate: 11,
      target_pct: 40,
      actual_pct: 35,
      weekly_series: [3, 5, 4, 6, 7, 5, 8, 6, 9, 10, 8, 11],
    },
    {
      pillar: "Kitchen",
      color: null,
      posts: 5,
      engagement: 1920,
      rate: null,
      target_pct: null,
      actual_pct: 12,
      weekly_series: [1, 2, 1, 3, 2, 2, 3, 2, 4, 3, 3, 4],
    },
  ],
  insights: [
    {
      tone: "terra" as const,
      title: "Support pillar over-indexed",
      body: "Consider pacing donor asks.",
    },
  ],
};

const PLATFORM_DATA = {
  platforms: [
    { platform: "instagram", posts: 14, engagement: 4300, reach: 48200, rate: 9.1 },
    { platform: "facebook", posts: 8, engagement: 1200, reach: 18000, rate: null },
  ],
  heatmap: {
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
  },
};

const RHYTHM_DATA = {
  weeks: [
    { label: "Jul 1–7", posted: 5, target: null },
    { label: "Jul 8–14", posted: 8, target: null },
  ],
  festivals: [
    { date: "2026-07-18", name: "Ratha Yatra", posts: 0, lift_pct: null, pending: true },
    { date: "2026-07-02", name: "Ekadashi", posts: 2, lift_pct: 42, pending: false },
  ],
  season: {
    total_posts: 13,
    consistency: { on_target_weeks: null, total_weeks: 4 },
    best_slot: { day: "Tuesday", hour_bucket: "9a" },
    avg_lead_days: 3.4,
  },
};

function seedMocks() {
  mockSummary.mockResolvedValue(SUMMARY);
  mockPosts.mockResolvedValue({ posts: POST_ROWS, total: 3 });
  mockPillars.mockResolvedValue(PILLAR_DATA);
  mockPlatforms.mockResolvedValue(PLATFORM_DATA);
  mockRhythm.mockResolvedValue(RHYTHM_DATA);
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

let createObjectURL: Mock;
let revokeObjectURL: Mock;
let anchorClick: ReturnType<typeof vi.spyOn>;

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(TODAY);
    seedMocks();
    createObjectURL = vi.fn(() => "blob:gv-results");
    revokeObjectURL = vi.fn();
    URL.createObjectURL = createObjectURL as unknown as typeof URL.createObjectURL;
    URL.revokeObjectURL = revokeObjectURL as unknown as typeof URL.revokeObjectURL;
    anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
  });

  afterEach(() => {
    anchorClick.mockRestore();
    vi.useRealTimers();
  });

  it("renders the header with the live date and the overview KPIs", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Results" })).toBeInTheDocument();
    expect(screen.getByText(/tuesday/i)).toBeInTheDocument();
    await screen.findByText("Posts published");
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText("18.2k")).toBeInTheDocument();
    expect(screen.getByText("4.8%")).toBeInTheDocument();
    expect(screen.getByText("48.2k")).toBeInTheDocument();
    // honesty rule: we don't track followers — Total reach replaces the design KPI
    expect(screen.getByText("Total reach")).toBeInTheDocument();
    expect(screen.queryByText(/new followers/i)).not.toBeInTheDocument();
    expect(mockSummary).toHaveBeenCalledWith("all");
  });

  it("shows the top post card, the peak callout, and Claude's insights", async () => {
    renderPage();
    await screen.findByText(/lakshmi and her calf — first morning/i);
    expect(screen.getByText("Top post")).toBeInTheDocument();
    expect(screen.getByText(/instagram · jul 3 · pillar: cow life/i)).toBeInTheDocument();
    expect(screen.getByText("12.1%")).toBeInTheDocument();
    // peak callout uses the real peak day, no festival correlation
    expect(screen.getByText("40 engagements")).toBeInTheDocument();
    expect(screen.getByText("Claude notices")).toBeInTheDocument();
    expect(screen.getByText("Herd posts outperform")).toBeInTheDocument();
    // tooltip pill keeps a visible outline in dark mode, where its ink fill
    // matches the card surface
    const tipRect = screen
      .getByText("40 engagements")
      .closest("g")
      ?.querySelector("rect");
    expect(tipRect).toHaveAttribute("stroke", "#fff8e7");
  });

  it("shows the imported-history caption when history posts exist", async () => {
    renderPage();
    await screen.findByText("Posts published");
    expect(
      screen.getByText(/includes imported facebook history\./i),
    ).toBeInTheDocument();
  });

  it("renders calm empty states for an all-empty summary", async () => {
    mockSummary.mockResolvedValue(EMPTY_SUMMARY);
    renderPage();
    await screen.findByText(/no standout post yet/i);
    expect(screen.getByText(/nothing to chart yet/i)).toBeInTheDocument();
    expect(screen.queryByText("Claude notices")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/includes imported facebook history/i),
    ).not.toBeInTheDocument();
  });

  it("refetches with the new range when the toggle changes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Posts published");
    await user.click(screen.getByRole("radio", { name: "7d" }));
    await waitFor(() => expect(mockSummary).toHaveBeenCalledWith("7d"));
  });

  it("keeps the header subtitle honest about the selected range", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Posts published");
    expect(
      screen.getByText("How your pasture fed the feed across your whole history."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "7d" }));
    expect(
      screen.getByText("How your pasture fed the feed this week."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "30d" }));
    expect(
      screen.getByText("How your pasture fed the feed this month."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/across your whole history/i),
    ).not.toBeInTheDocument();
  });

  it("defaults to All time so the imported history shows on first load", async () => {
    const user = userEvent.setup();
    renderPage();
    // the imported history ends before the short windows — defaulting to
    // "all" keeps the first paint from reading as all-zeros
    await screen.findByText("Posts published");
    expect(screen.getByRole("radio", { name: "All time" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(mockSummary).toHaveBeenCalledWith("all");
    await user.click(screen.getByRole("radio", { name: "30d" }));
    await waitFor(() => expect(mockSummary).toHaveBeenCalledWith("30d"));
  });

  it("keeps window captions honest on the all-time range", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Posts published");
    await user.click(screen.getByRole("tab", { name: /per platform/i }));
    await screen.findByText(/from your full posting history · based on 22 posts/i);
    expect(mockPlatforms).toHaveBeenCalledWith("all");
    expect(screen.queryByText(/from your last/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /rhythm/i }));
    await screen.findByText(/you've published 13 posts in all\./i);
    expect(mockRhythm).toHaveBeenCalledWith("all");
    expect(screen.queryByText(/posts this month\./i)).not.toBeInTheDocument();
  });

  it("only fetches a tab's data when the tab activates", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Posts published");
    expect(mockRhythm).not.toHaveBeenCalled();
    expect(mockPosts).not.toHaveBeenCalled();
    await user.click(screen.getByRole("tab", { name: /rhythm/i }));
    await waitFor(() => expect(mockRhythm).toHaveBeenCalledWith("all"));
  });

  it("renders the posts table with trend cells and honest rate placeholders", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per post/i }));
    await screen.findByText("Lakshmi and her calf");
    expect(mockPosts).toHaveBeenCalledWith("all", 20, 0);
    expect(screen.getByText(/showing 3 of 3/i)).toBeInTheDocument();
    expect(screen.getByText("vs avg")).toBeInTheDocument();
    expect(screen.getByText("below")).toBeInTheDocument();
    expect(screen.getByText("— flat")).toBeInTheDocument();
    expect(screen.getByText("3,442")).toBeInTheDocument();
    // null pillar and null rate render as "—"
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("button", { name: /show more/i })).not.toBeInTheDocument();
  });

  it("appends the next page of posts via Show more", async () => {
    const firstPage = Array.from({ length: 20 }, (_, i) => ({
      ...POST_ROWS[0],
      id: i + 1,
      title: `Post number ${i + 1}`,
    }));
    const secondPage = Array.from({ length: 5 }, (_, i) => ({
      ...POST_ROWS[0],
      id: 21 + i,
      title: `Post number ${21 + i}`,
    }));
    mockPosts.mockImplementation((_range, _limit, offset) =>
      Promise.resolve(
        (offset ?? 0) === 0
          ? { posts: firstPage, total: 25 }
          : { posts: secondPage, total: 25 },
      ),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per post/i }));
    await screen.findByText(/showing 20 of 25/i);
    await user.click(screen.getByRole("button", { name: /show more/i }));
    await screen.findByText(/showing 25 of 25/i);
    expect(mockPosts).toHaveBeenCalledWith("all", 20, 20);
    expect(screen.getByText("Post number 25")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /show more/i })).not.toBeInTheDocument();
  });

  it("shows an empty state when no posts exist in the window", async () => {
    mockPosts.mockResolvedValue({ posts: [], total: 0 });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per post/i }));
    await screen.findByText(/no posts in this window/i);
  });

  it("stops paging when a page comes back empty despite a stale total", async () => {
    const firstPage = Array.from({ length: 20 }, (_, i) => ({
      ...POST_ROWS[0],
      id: i + 1,
      title: `Post number ${i + 1}`,
    }));
    mockPosts.mockImplementation((_range, _limit, offset) =>
      Promise.resolve(
        (offset ?? 0) === 0
          ? { posts: firstPage, total: 25 }
          : { posts: [], total: 25 },
      ),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per post/i }));
    await screen.findByText(/showing 20 of 25/i);
    await user.click(screen.getByRole("button", { name: /show more/i }));
    // the empty page ends pagination instead of re-requesting offset 20 forever
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: /show more/i }),
      ).not.toBeInTheDocument(),
    );
    expect(mockPosts).toHaveBeenCalledTimes(2);
  });

  it("announces tab loading to screen readers", async () => {
    mockPillars.mockImplementation(() => new Promise<never>(() => {}));
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per pillar/i }));
    expect(
      screen.getByRole("status", { name: "Loading analytics" }),
    ).toBeInTheDocument();
  });

  it("renders pillar cards with targets, no-target captions, and insights", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per pillar/i }));
    await screen.findByText(/which pillars fed the feed/i);
    expect(screen.getByText("Cow Life")).toBeInTheDocument();
    expect(screen.getByText("Actual 35%")).toBeInTheDocument();
    expect(screen.getByText("Target 40%")).toBeInTheDocument();
    expect(screen.getByText("Kitchen")).toBeInTheDocument();
    expect(screen.getByText("No target set")).toBeInTheDocument();
    expect(screen.getByText("Support pillar over-indexed")).toBeInTheDocument();
    // honest labels: the mini chart shows posts-per-week, not engagement rate
    expect(screen.getAllByText("Posting rhythm")).toHaveLength(2);
    expect(screen.queryByText("Engagement rate")).not.toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Cow Life posts per week, oldest to newest",
      }),
    ).toBeInTheDocument();
  });

  it("renders platform cards without followers, sentiment, or benchmarks", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per platform/i }));
    await screen.findByText("Instagram");
    expect(screen.getByText("9.1%")).toBeInTheDocument();
    expect(screen.getByText("Facebook")).toBeInTheDocument();
    expect(screen.getByText("48,200")).toBeInTheDocument();
    // honesty rule: no fabricated rows
    expect(screen.queryByText(/followers/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sentiment/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/benchmark/i)).not.toBeInTheDocument();
    // heatmap with real peak + sample size caption
    expect(
      screen.getByRole("img", { name: /peak: tue around 9a/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/based on 22 posts/i)).toBeInTheDocument();
  });

  it("shows an empty state instead of a grey heatmap when sample_size is 0", async () => {
    mockPlatforms.mockResolvedValue({
      platforms: [],
      heatmap: { days: [], hour_buckets: [], peak: null, sample_size: 0 },
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per platform/i }));
    await screen.findByText(/not enough posting history yet/i);
    expect(screen.getByText(/no platform results yet/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /engagement by day of week/i }),
    ).not.toBeInTheDocument();
  });

  it("renders cadence without target markers and festivals with lift", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /rhythm/i }));
    await screen.findByText("Jul 1–7");
    expect(screen.getByText("Jul 8–14")).toBeInTheDocument();
    expect(screen.getByText("Posted")).toBeInTheDocument();
    // target is always null today — no target legend or marker
    expect(screen.queryByText(/weekly target/i)).not.toBeInTheDocument();
    expect(screen.getByText("Ratha Yatra")).toBeInTheDocument();
    expect(screen.getByText("upcoming")).toBeInTheDocument();
    expect(screen.getByText("Ekadashi")).toBeInTheDocument();
    expect(screen.getByText("+42%")).toBeInTheDocument();
  });

  it("builds the season card from real data and omits null stats", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /rhythm/i }));
    await screen.findByText(/you've published 13 posts in all\./i);
    expect(screen.getByText("Tuesday 9a")).toBeInTheDocument();
    expect(screen.getByText("3.4 days")).toBeInTheDocument();
    // consistency row omitted while on_target_weeks is null
    expect(screen.queryByText(/consistency/i)).not.toBeInTheDocument();
  });

  it("exports a CSV blob from freshly fetched pages, never the loaded tab rows", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: /per post/i }));
    await screen.findByText(/showing 3 of 3/i);
    mockPosts.mockClear();
    await user.click(screen.getByRole("button", { name: /export csv/i }));
    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1));
    // export refetches within the backend's 100-row limit — it never reuses
    // the tab's (possibly truncated) rows
    expect(mockPosts).toHaveBeenCalledWith("all", 100, 0);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toContain("text/csv");
    const text = await blob.text();
    expect(text).toContain("Title,Pillar,Platforms,Date,Engagement,Rate,Trend,Source");
    expect(text).toContain("Lakshmi and her calf");
    expect(anchorClick).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:gv-results");
  });

  it("pages through every post when exporting before the posts tab loads", async () => {
    const total = 150;
    const allRows = Array.from({ length: total }, (_, i) => ({
      ...POST_ROWS[0],
      id: i + 1,
      title: `Post number ${i + 1}`,
    }));
    mockPosts.mockImplementation((_range, limit = 20, offset = 0) =>
      Promise.resolve({ posts: allRows.slice(offset, offset + limit), total }),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Posts published");
    expect(mockPosts).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /export csv/i }));
    await waitFor(() => expect(createObjectURL).toHaveBeenCalledTimes(1));
    expect(mockPosts).toHaveBeenNthCalledWith(1, "all", 100, 0);
    expect(mockPosts).toHaveBeenNthCalledWith(2, "all", 100, 100);
    expect(mockPosts).toHaveBeenCalledTimes(2);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const text = await blob.text();
    // header + all 150 rows — nothing silently truncated
    expect(text.trim().split("\n")).toHaveLength(151);
    expect(text).toContain("Post number 150");
  });
});
