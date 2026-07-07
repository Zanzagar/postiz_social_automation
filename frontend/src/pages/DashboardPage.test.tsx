import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { CalendarEntry, ContentRow } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getDrafts: vi.fn(),
    getCalendar: vi.fn(),
    getHealth: vi.fn(),
    getPillars: vi.fn(),
    getAnalyticsOverview: vi.fn(),
    getFestivals: vi.fn(),
    getKnowledgeStatus: vi.fn(),
    holdContent: vi.fn(),
    resumeContent: vi.fn(),
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

import { api } from "@/lib/api";
const mockGetDrafts = vi.mocked(api.getDrafts);
const mockGetCalendar = vi.mocked(api.getCalendar);
const mockGetHealth = vi.mocked(api.getHealth);
const mockGetPillars = vi.mocked(api.getPillars);
const mockGetOverview = vi.mocked(api.getAnalyticsOverview);
const mockGetFestivals = vi.mocked(api.getFestivals);
const mockGetKnowledge = vi.mocked(api.getKnowledgeStatus);
const mockHold = vi.mocked(api.holdContent);
const mockResume = vi.mocked(api.resumeContent);

// Frozen "today" — Monday, July 6 2026, 9:00 AM local time.
const MORNING = new Date("2026-07-06T09:00:00");

function row(overrides: Partial<ContentRow>): ContentRow {
  return {
    row_number: 1,
    date: "2026-07-06",
    content_pillar: "Cow Life",
    raw_text: "Tabby greets the sunrise",
    media_url: null,
    platforms: { instagram: true },
    status: "draft",
    captions: { instagram: "caption" },
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

const postedRow = row({
  row_number: 10,
  status: "posted",
  raw_text: "Sparkle at morning milking",
  posted_at: "2026-07-06T08:15:00",
  platforms: { instagram: true, facebook: true },
});

const pendingRow = row({
  row_number: 11,
  raw_text: "Tabby greets the sunrise",
  captions: { instagram: "IG caption", facebook: "FB caption" },
  platforms: { instagram: true, facebook: true },
});

const countdownRow = row({
  row_number: 12,
  status: "approved",
  raw_text: "Dennis in the cheese room",
  auto_publish_at: "2026-07-06T16:30:00",
});

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

const calendarEntries: CalendarEntry[] = [
  entry({ row_number: 10, status: "posted", raw_text: "Sparkle at morning milking" }),
  entry({ row_number: 12, status: "approved", raw_text: "Dennis in the cheese room" }),
  // streak history: posted yesterday and the day before
  entry({ row_number: 8, status: "posted", date: "2026-07-05", raw_text: "Brisham grazing" }),
  entry({ row_number: 7, status: "posted", date: "2026-07-04", raw_text: "Daring Denise" }),
];

function seedMocks() {
  mockGetDrafts.mockResolvedValue([postedRow, pendingRow, countdownRow]);
  mockGetCalendar.mockResolvedValue({ entries: calendarEntries, total: calendarEntries.length });
  mockGetHealth.mockResolvedValue({ services: [], errors: [] });
  mockGetPillars.mockResolvedValue([
    {
      id: 1,
      name: "Cow Life",
      description: null,
      color: "#4a7c59",
      target: 40,
      is_active: true,
      sort_order: 1,
    },
  ]);
  mockGetOverview.mockResolvedValue({
    total_posts: 42,
    total_engagement: 8412,
    avg_engagement: 200,
    total_reach: 34200,
    total_impressions: 51000,
  });
  mockGetFestivals.mockResolvedValue([
    {
      name: "Ratha Yatra",
      date: "2026-07-18",
      significance: "Festival of chariots",
      suggested_content_angles: [],
      topic: "festival",
      content_pillar: "Spiritual",
    },
  ]);
  mockGetKnowledge.mockResolvedValue({
    sources: [{ name: "gitavalley.org", type: "site", page_count: 110 }],
    knowledge_entries: 1089,
  });
  mockHold.mockResolvedValue({ ...countdownRow, held_at: "2026-07-06T09:01:00" });
  mockResume.mockResolvedValue(countdownRow);
}

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(MORNING);
    seedMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the morning greeting before noon", async () => {
    renderDashboard();
    expect(screen.getByText(/morning review/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /good morning\./i }),
    ).toBeInTheDocument();
    await waitFor(() => expect(mockGetDrafts).toHaveBeenCalled());
  });

  it("shows the afternoon greeting between noon and 5pm", async () => {
    vi.setSystemTime(new Date("2026-07-06T14:00:00"));
    renderDashboard();
    expect(screen.getByText(/afternoon check-in/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /good afternoon\./i }),
    ).toBeInTheDocument();
    await waitFor(() => expect(mockGetDrafts).toHaveBeenCalled());
  });

  it("shows the evening greeting after 5pm", async () => {
    vi.setSystemTime(new Date("2026-07-06T20:00:00"));
    renderDashboard();
    expect(screen.getByText(/evening publish/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /good evening\./i }),
    ).toBeInTheDocument();
    await waitFor(() => expect(mockGetDrafts).toHaveBeenCalled());
  });

  it("computes ritual strip stats from real data", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByTestId("stat-posted")).toHaveTextContent("1");
    });
    expect(screen.getByTestId("stat-review")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-scheduled")).toHaveTextContent("1");
    // posted today + 2 consecutive prior days
    expect(screen.getByTestId("stat-streak")).toHaveTextContent("3");
  });

  it("summarizes real data in the subtitle", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(
        screen.getByText(
          /1 post has gone out, 1 is ready for your blessing, and 1 is scheduled for today\./i,
        ),
      ).toBeInTheDocument();
    });
  });

  it("renders today's rhythm rows with status chips", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Sparkle at morning milking")).toBeInTheDocument();
    });
    expect(screen.getByText("Dennis in the cheese room")).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(screen.getAllByText("Review").length).toBeGreaterThanOrEqual(1);
  });

  it("holds an auto-publish row via the countdown chip", async () => {
    const user = userEvent.setup();
    renderDashboard();
    const holdButton = await screen.findByRole("button", {
      name: /pause and hold for review/i,
    });
    await user.click(holdButton);
    await waitFor(() => {
      expect(mockHold).toHaveBeenCalledWith(12);
    });
  });

  it("shows the blessing card with the first pending draft", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByTestId("blessing-card")).toBeInTheDocument();
    });
    const card = screen.getByTestId("blessing-card");
    expect(within(card).getByText("Tabby greets the sunrise")).toBeInTheDocument();
    expect(
      within(card).getByRole("link", { name: /review captions/i }),
    ).toHaveAttribute("href", "/drafts");
  });

  it("shows the quiet card when nothing is pending", async () => {
    mockGetDrafts.mockResolvedValue([postedRow]);
    renderDashboard();
    await waitFor(() => {
      expect(
        screen.getByText(/the pasture is quiet — nothing waiting\./i),
      ).toBeInTheDocument();
    });
    expect(screen.queryByTestId("blessing-card")).not.toBeInTheDocument();
  });

  it("renders upcoming festivals with days-until", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Ratha Yatra")).toBeInTheDocument();
    });
    expect(screen.getByText("in 12d")).toBeInTheDocument();
  });

  it("dispatches the command palette event from the search button", async () => {
    const listener = vi.fn();
    window.addEventListener("gv:open-command-palette", listener);
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("button", { name: /search/i }));
    expect(listener).toHaveBeenCalled();
    window.removeEventListener("gv:open-command-palette", listener);
    await waitFor(() => expect(mockGetDrafts).toHaveBeenCalled());
  });
});
