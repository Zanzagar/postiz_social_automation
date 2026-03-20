import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { CalendarPage } from "./CalendarPage";

import userEvent from "@testing-library/user-event";

vi.mock("@/lib/api", () => ({
  api: {
    getCalendar: vi.fn(),
    iterate: vi.fn(),
    getIterations: vi.fn(),
    editDraft: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetCalendar = vi.mocked(api.getCalendar);

const sampleEntries: Array<{
  row_number: number;
  date: string;
  content_pillar: string;
  raw_text: string;
  status: string;
  platforms: Record<string, boolean>;
  captions: Record<string, string | null>;
}> = [
  {
    row_number: 1,
    date: "2026-03-17",
    content_pillar: "spiritual",
    raw_text: "Morning meditation",
    status: "draft",
    platforms: { instagram: true },
    captions: { instagram: "Caption" },
  },
  {
    row_number: 2,
    date: "2026-03-18",
    content_pillar: "farm",
    raw_text: "Cow update",
    status: "scheduled",
    platforms: { facebook: true },
    captions: { facebook: "FB cap" },
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
  beforeEach(() => vi.clearAllMocks());

  it("shows loading state", () => {
    mockGetCalendar.mockReturnValue(new Promise(() => {}));
    renderCalendar();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders calendar entries grouped by date in list view", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
      expect(screen.getByText(/cow update/i)).toBeInTheDocument();
    });
  });

  it("shows empty state when no entries", async () => {
    mockGetCalendar.mockResolvedValue({ entries: [], total: 0 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByText(/no scheduled content/i)).toBeInTheDocument();
    });
  });

  // --- View toggle ---

  it("shows view toggle tabs (monthly, weekly, list)", async () => {
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /monthly/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /weekly/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /list/i })).toBeInTheDocument();
    });
  });

  it("switches to monthly view when tab clicked", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /monthly/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("tab", { name: /monthly/i }));

    // Monthly view should show day-of-week headers
    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
      expect(screen.getByText("Mon")).toBeInTheDocument();
    });
  });

  // --- ContentEditor integration ---

  it("opens ContentEditor when clicking a calendar entry", async () => {
    const user = userEvent.setup();
    mockGetCalendar.mockResolvedValue({ entries: sampleEntries, total: 2 });
    vi.mocked(api.getIterations).mockResolvedValue([]);
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/morning meditation/i));

    await waitFor(() => {
      expect(screen.getByText(/refine content/i)).toBeInTheDocument();
    });
  });
});
