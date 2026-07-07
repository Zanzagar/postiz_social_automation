import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CalendarPage } from "./CalendarPage";
import type { Festival, Pillar } from "@/lib/api";
import type { CalendarEntryX } from "@/components/calendar/calendar-utils";

vi.mock("@/lib/api", () => ({
  api: {
    getCalendar: vi.fn(),
    getPillars: vi.fn(),
    getFestivals: vi.fn(),
    createCalendarPlan: vi.fn(),
    approveCalendarPlan: vi.fn(),
    deleteCalendarPlan: vi.fn(),
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

// The unified editor is another surface — mock it so tests only assert wiring.
vi.mock("@/components/content/ContentEditorSheet", () => ({
  ContentEditorSheet: ({ rowId }: { rowId: number | null }) =>
    rowId === null ? null : (
      <div data-testid="editor-sheet">editing row {rowId}</div>
    ),
}));

import { api } from "@/lib/api";
const mockGetCalendar = vi.mocked(api.getCalendar);
const mockGetPillars = vi.mocked(api.getPillars);
const mockGetFestivals = vi.mocked(api.getFestivals);

const samplePillars: Pillar[] = [
  {
    id: 1,
    name: "Cow Life",
    description: null,
    color: "#4a7c59",
    target: 40,
    is_active: true,
    sort_order: 0,
  },
  {
    id: 2,
    name: "Farm Ops",
    description: null,
    color: "#b08968",
    target: 25,
    is_active: true,
    sort_order: 1,
  },
];

// System time is frozen to Wed 2026-07-08 — both entries fall in that week
// (Mon Jul 6 – Sun Jul 12).
const sampleEntries: CalendarEntryX[] = [
  {
    row_number: 11,
    date: "2026-07-07T10:00:00",
    content_pillar: "Cow Life",
    raw_text: "Tabby greets the sunrise",
    status: "scheduled",
    platforms: { instagram: true, facebook: true },
    captions: { instagram: "Caption", facebook: "FB cap" },
  },
  {
    row_number: 12,
    date: "2026-07-09T16:30:00",
    content_pillar: "Farm Ops",
    raw_text: "Dennis inspects the new fence",
    status: "approved",
    platforms: { instagram: true },
    captions: { instagram: "Fence cap" },
    auto_publish_at: "2026-07-09T16:30:00",
  },
];

const sampleFestivals: Festival[] = [
  {
    name: "Guru Purnima",
    date: "2026-07-18",
    significance: "Honoring the guru",
    suggested_content_angles: [],
    topic: "festival",
    content_pillar: "Community",
  },
];

function renderCalendar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CalendarPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Fixtures use fixed July 2026 dates; freeze Date (only) so the calendar's
    // "current" week contains them. Timers stay real so waitFor/userEvent work.
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-07-08T09:00:00"));

    mockGetPillars.mockResolvedValue(samplePillars);
    mockGetFestivals.mockResolvedValue(sampleFestivals);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a loading skeleton while the calendar loads", () => {
    mockGetCalendar.mockReturnValue(new Promise(() => {}));
    renderCalendar();
    expect(
      screen.getByRole("status", { name: /loading calendar/i }),
    ).toBeInTheDocument();
  });

  it("renders entries in the default week view", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
      expect(
        screen.getByText(/dennis inspects the new fence/i),
      ).toBeInTheDocument();
    });
  });

  it("switches views via the segmented control (radiogroup)", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();

    const group = screen.getByRole("radiogroup", { name: /calendar view/i });
    expect(group).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
    });

    // List view: empty day rows invite "add a post"; entries render as rows
    await user.click(screen.getByRole("radio", { name: /list/i }));
    expect(screen.getAllByText(/nothing scheduled/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();

    // Month view: range label becomes the month name
    await user.click(screen.getByRole("radio", { name: /month/i }));
    expect(screen.getByText("July 2026")).toBeInTheDocument();

    // Back to week
    await user.click(screen.getByRole("radio", { name: /week/i }));
    expect(screen.getByText(/jul 6 – jul 12, 2026/i)).toBeInTheDocument();
  });

  it("shows the quiet auto dot only for entries with auto_publish_at", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/dennis inspects the new fence/i)).toBeInTheDocument();
    });
    // One entry has auto_publish_at → exactly one "auto" marker in the week grid
    expect(screen.getAllByText("auto")).toHaveLength(1);
  });

  it("shows the auto dot on list rows too", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
    });
    await user.click(screen.getByRole("radio", { name: /list/i }));
    expect(screen.getAllByText("auto")).toHaveLength(1);
  });

  it("renders upcoming festivals in the side rail with days-until", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText("Guru Purnima")).toBeInTheDocument();
    });
    // Jul 18 is 10 days after the frozen Jul 8
    expect(screen.getByText(/in 10 days/i)).toBeInTheDocument();
  });

  it("counts pillars this week in the side rail", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    // Wait for entries to land, then the rail lists both pillar names
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/pillars this week/i)).toBeInTheDocument();
    expect(screen.getByText("Cow Life")).toBeInTheDocument();
    expect(screen.getByText("Farm Ops")).toBeInTheDocument();
  });

  it("opens the content editor when an entry is clicked", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/tabby greets the sunrise/i));

    await waitFor(() => {
      expect(screen.getByTestId("editor-sheet")).toHaveTextContent(
        "editing row 11",
      );
    });
  });

  it("shows the quiet-week empty state when the week has no entries", async () => {
    mockGetCalendar.mockResolvedValue({ entries: [], total: 0 });
    renderCalendar();
    await waitFor(() => {
      expect(
        screen.getByText(/a quiet week on the pasture/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /plant something/i }),
    ).toBeInTheDocument();
  });

  it("opens the plan dialog from the Plan week button", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/tabby greets the sunrise/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /plan week/i }));

    await waitFor(() => {
      expect(screen.getByText(/plan content calendar/i)).toBeInTheDocument();
    });
  });
});
