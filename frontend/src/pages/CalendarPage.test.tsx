import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { CalendarPage } from "./CalendarPage";

vi.mock("@/lib/api", () => ({
  api: {
    getCalendar: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetCalendar = vi.mocked(api.getCalendar);

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

  it("renders calendar entries grouped by date", async () => {
    mockGetCalendar.mockResolvedValue({
      entries: [
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
      ],
      total: 2,
    });
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
});
