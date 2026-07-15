import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { KnowledgePage } from "./KnowledgePage";
import type {
  BrowseResponse,
  KnowledgeEntry,
  KnowledgeStats,
  KnowledgeStatusResponse,
} from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getKnowledgeStatus: vi.fn(),
    getKnowledgeStats: vi.fn(),
    getPillars: vi.fn(),
    getCrawlProgress: vi.fn(),
    browseKnowledge: vi.fn(),
    searchKnowledge: vi.fn(),
    getKnowledgeGraph: vi.fn(),
    triggerCrawl: vi.fn(),
    triggerSocialImport: vi.fn(),
    askKnowledge: vi.fn(),
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
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

// Heavy canvas lib — replaced with a marker div (loaded lazily by GraphTab).
vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="force-graph" />,
}));

import { api } from "@/lib/api";
import { toast } from "sonner";

const mockGetStatus = vi.mocked(api.getKnowledgeStatus);
const mockGetStats = vi.mocked(api.getKnowledgeStats);
const mockGetPillars = vi.mocked(api.getPillars);
const mockGetProgress = vi.mocked(api.getCrawlProgress);
const mockBrowse = vi.mocked(api.browseKnowledge);
const mockSearch = vi.mocked(api.searchKnowledge);
const mockGetGraph = vi.mocked(api.getKnowledgeGraph);
const mockTriggerCrawl = vi.mocked(api.triggerCrawl);
const mockTriggerImport = vi.mocked(api.triggerSocialImport);
const mockAsk = vi.mocked(api.askKnowledge);

const NOW = new Date("2026-07-14T09:00:00");

const statusData: KnowledgeStatusResponse = {
  sources: [
    { name: "gitavalley", type: "web", page_count: 84, last_crawled: "2026-07-13T09:00:00" },
    { name: "iskcon", type: "web", page_count: 26, last_crawled: "2026-07-13T09:05:00" },
    { name: "facebook", type: "social", post_count: 100, last_imported: "2026-07-12T10:00:00" },
  ],
  knowledge_entries: 1089,
};

const statsData: KnowledgeStats = {
  total_pages: 110,
  total_knowledge: 1089,
  pages_with_knowledge: 100,
  pages_without_knowledge: 10,
  by_type: [
    { type: "description", count: 600 },
    { type: "program", count: 250 },
    { type: "event", count: 150 },
    { type: "quote", count: 89 },
  ],
  by_topic: [
    { topic: "Community programs", count: 300 },
    { topic: "Festivals", count: 200 },
  ],
  by_pillar: [
    { pillar: "Cow Life", count: 500 },
    { pillar: "Spiritual", count: 400 },
  ],
  coverage_gaps: [
    {
      title: "Photo Gallery 2024",
      site: "gitavalley",
      url: "https://gitavalley.org/gallery-2024",
      fact_count: 0,
    },
  ],
};

const factOne: KnowledgeEntry = {
  id: 1,
  fact_type: "program",
  content: "Sunday Feast — open to all, weekly at 4pm.",
  topic: "Community programs",
  pillar: "Spiritual",
  keywords: ["sunday", "feast"],
  page_title: "Sunday Feast",
  page_url: "https://gitavalley.org/feast",
  site: "gitavalley",
};

const factTwo: KnowledgeEntry = {
  id: 2,
  fact_type: "quote",
  content: "The cows are mothers, not livestock.",
  topic: "Cow protection",
  pillar: "Cow Life",
  keywords: ["cows"],
  page_title: "Our Cows",
  page_url: "https://gitavalley.org/cows",
  site: "iskcon",
};

const browseData: BrowseResponse = {
  results: [factOne, factTwo],
  total: 42,
  page: 1,
  per_page: 20,
  total_pages: 3,
};

const idleProgress = { running: false, source: "", current: 0, total: 0, phase: "" };

function seedMocks() {
  mockGetStatus.mockResolvedValue(statusData);
  mockGetStats.mockResolvedValue(statsData);
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
    {
      id: 2,
      name: "Spiritual",
      description: null,
      color: null,
      target: 5,
      is_active: true,
      sort_order: 2,
    },
  ]);
  mockGetProgress.mockResolvedValue(idleProgress);
  mockBrowse.mockResolvedValue(browseData);
  mockSearch.mockResolvedValue({
    results: [
      {
        id: 9,
        fact_type: "event",
        content: "Rama Navami celebration in spring.",
        pillar: "Spiritual",
        page_title: "Festivals",
        page_url: "https://gitavalley.org/festivals",
        site: "gitavalley",
      },
    ],
    count: 1,
  });
  mockGetGraph.mockResolvedValue({
    nodes: [
      { id: "t1", label: "Festivals", type: "topic", size: 8 },
      { id: "p1", label: "Sunday Feast", type: "page", size: 3, site: "gitavalley" },
    ],
    links: [{ source: "t1", target: "p1" }],
  });
  mockTriggerCrawl.mockResolvedValue({ status: "started" });
  mockTriggerImport.mockResolvedValue({ status: "started" });
  mockAsk.mockResolvedValue({ answer: null, sources: [], answered_by: "search_only" });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <KnowledgePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("KnowledgePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    seedMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the header and metric strip from real data", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /what claude has read/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("110")).toBeInTheDocument();
    });
    expect(screen.getByText("gitavalley (84) · iskcon (26)")).toBeInTheDocument();
    expect(screen.getByText("1,089")).toBeInTheDocument();
    expect(screen.getByText("facebook 100")).toBeInTheDocument();
    expect(screen.getByText(/pages with zero extracted facts/i)).toBeInTheDocument();
  });

  it("builds pillar filter options dynamically from getPillars", async () => {
    renderPage();
    const group = await screen.findByRole("tablist", { name: /filter by pillar/i });
    expect(within(group).getByRole("tab", { name: "All" })).toBeInTheDocument();
    expect(within(group).getByRole("tab", { name: "Cow Life" })).toBeInTheDocument();
    expect(within(group).getByRole("tab", { name: "Spiritual" })).toBeInTheDocument();
  });

  it("browses by default and passes the pillar filter to browseKnowledge", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => {
      expect(mockBrowse).toHaveBeenCalledWith(
        expect.objectContaining({ page: 1, pillar: undefined }),
      );
    });
    const group = await screen.findByRole("tablist", { name: /filter by pillar/i });
    await user.click(within(group).getByRole("tab", { name: "Cow Life" }));
    await waitFor(() => {
      expect(mockBrowse).toHaveBeenCalledWith(
        expect.objectContaining({ pillar: "Cow Life", page: 1 }),
      );
    });
  });

  it("switches to searchKnowledge when a query is submitted", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Sunday Feast — open to all, weekly at 4pm.");
    await user.type(screen.getByLabelText(/search facts/i), "rama{Enter}");
    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("rama", undefined);
    });
    expect(
      await screen.findByText("Rama Navami celebration in spring."),
    ).toBeInTheDocument();
  });

  it("requests the next page via server-side pagination", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Page 1 of 3");
    await user.click(screen.getByRole("button", { name: /next page/i }));
    await waitFor(() => {
      expect(mockBrowse).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }));
    });
  });

  it("shows an empty state when browse returns no facts", async () => {
    mockBrowse.mockResolvedValue({
      results: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 1,
    });
    renderPage();
    expect(
      await screen.findByText(/nothing in the hayloft for that/i),
    ).toBeInTheDocument();
  });

  it("copies a fact to the clipboard", async () => {
    const user = userEvent.setup();
    // Defined after userEvent.setup() so its own clipboard stub doesn't shadow ours.
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    renderPage();
    await screen.findByText("Sunday Feast — open to all, weekly at 4pm.");
    await user.click(screen.getAllByRole("button", { name: /copy fact/i })[0]);
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("Sunday Feast — open to all, weekly at 4pm.");
    });
    expect(toast.success).toHaveBeenCalled();
  });

  it("shows the crawl banner while a crawl is running", async () => {
    mockGetProgress.mockResolvedValue({
      running: true,
      source: "gitavalley.org",
      current: 12,
      total: 84,
      phase: "extracting: Daily Schedule",
    });
    renderPage();
    expect(await screen.findByText(/crawling gitavalley\.org/i)).toBeInTheDocument();
    expect(screen.getByText("12/84")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("hides the crawl banner when idle", async () => {
    renderPage();
    await waitFor(() => expect(mockGetProgress).toHaveBeenCalled());
    expect(screen.queryByText(/crawling/i)).not.toBeInTheDocument();
  });

  it("fires triggerCrawl from the Re-crawl header button", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /re-crawl/i }));
    await waitFor(() => expect(mockTriggerCrawl).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
  });

  it("renders sources with re-sync wired per source kind", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: "Sources" }));
    expect(await screen.findByText("gitavalley.org (WordPress)")).toBeInTheDocument();
    expect(screen.getByText("Facebook Page — Gita Valley")).toBeInTheDocument();
    expect(screen.getByText(/websites are hard-wired/i)).toBeInTheDocument();
    expect(screen.getByText(/content-hash skip/i)).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /re-sync facebook page — gita valley/i }),
    );
    await waitFor(() => expect(mockTriggerImport).toHaveBeenCalled());
    expect(mockTriggerCrawl).not.toHaveBeenCalled();
  });

  it("renders insights breakdowns and coverage gaps from stats", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: "Insights" }));
    expect(await screen.findByText("By fact type")).toBeInTheDocument();
    expect(screen.getByText("By pillar")).toBeInTheDocument();
    expect(screen.getByText("By topic")).toBeInTheDocument();
    expect(screen.getByText("Photo Gallery 2024")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view page/i })).toHaveAttribute(
      "href",
      "https://gitavalley.org/gallery-2024",
    );
  });

  it("renders the force graph on the Graph tab", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("tab", { name: "Graph" }));
    expect(await screen.findByTestId("force-graph")).toBeInTheDocument();
    expect(mockGetGraph).toHaveBeenCalled();
  });

  it("shows a Claude answer with its sources in the ask sheet", async () => {
    mockAsk.mockResolvedValue({
      answer: "Lakshmi is one of the gentlest mothers in the herd.",
      sources: [
        {
          content: "Lakshmi arrived in the winter of 2022.",
          fact_type: "description",
          topic: null,
          pillar: null,
          site: "gitavalley",
          page_title: "Our Cows",
          score: 0.9,
        },
      ],
      answered_by: "claude",
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /ask what it knows/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Ask the farm")).toBeInTheDocument();
    await user.type(
      within(dialog).getByLabelText(/ask what claude knows/i),
      "What do you know about Lakshmi?",
    );
    await user.click(within(dialog).getByRole("button", { name: "Ask" }));
    expect(
      await within(dialog).findByText(
        "Lakshmi is one of the gentlest mothers in the herd.",
      ),
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/sources claude used/i)).toBeInTheDocument();
    expect(within(dialog).getByText("Our Cows")).toBeInTheDocument();
    expect(mockAsk).toHaveBeenCalledWith("What do you know about Lakshmi?");
  });

  it("shows a calm note for search_only answers", async () => {
    mockAsk.mockResolvedValue({
      answer: null,
      sources: [
        {
          content: "Volunteer day happens monthly.",
          fact_type: "program",
          topic: null,
          pillar: null,
          site: "gitavalley",
          page_title: "Volunteer",
          score: 0.5,
        },
      ],
      answered_by: "search_only",
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /ask what it knows/i }));
    await user.click(screen.getByRole("button", { name: "Who are our named cows?" }));
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(
      await screen.findByText(/a written answer wasn't available just now/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Volunteer")).toBeInTheDocument();
    expect(mockAsk).toHaveBeenCalledWith("Who are our named cows?");
  });

  it("shows an empty state when the ask returns nothing", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /ask what it knows/i }));
    await user.type(screen.getByLabelText(/ask what claude knows/i), "quantum tractors");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(/nothing on that yet/i)).toBeInTheDocument();
  });
});
