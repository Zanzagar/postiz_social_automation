import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SuggestionsPage } from "./SuggestionsPage";

vi.mock("@/lib/api", () => ({
  api: {
    getSuggestions: vi.fn(),
    iterate: vi.fn(),
    getIterations: vi.fn(),
    editDraft: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetSuggestions = vi.mocked(api.getSuggestions);

const sampleSuggestion = {
  id: 1,
  type: "gap",
  title: "Spring planting ceremony photos",
  note: "Seasonal relevance",
  pillar: "farm",
  date: "2026-03-20",
  days_until: 4,
  status: "pending",
};

function renderSuggestions() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SuggestionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SuggestionsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading state", () => {
    mockGetSuggestions.mockReturnValue(new Promise(() => {}));
    renderSuggestions();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders suggestion cards", async () => {
    mockGetSuggestions.mockResolvedValue({ suggestions: [sampleSuggestion] });
    renderSuggestions();
    await waitFor(() => {
      expect(screen.getByText(/spring planting/i)).toBeInTheDocument();
      expect(screen.getByText(/seasonal relevance/i)).toBeInTheDocument();
    });
  });

  it("shows empty state", async () => {
    mockGetSuggestions.mockResolvedValue({ suggestions: [] });
    renderSuggestions();
    await waitFor(() => {
      expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
    });
  });

  // --- ContentEditor integration ---

  it("opens ContentEditor in create mode when clicking suggestion", async () => {
    const user = userEvent.setup();
    mockGetSuggestions.mockResolvedValue({ suggestions: [sampleSuggestion] });
    vi.mocked(api.getIterations).mockResolvedValue([]);
    renderSuggestions();

    await waitFor(() => {
      expect(screen.getByText(/spring planting/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/spring planting/i));

    await waitFor(() => {
      expect(screen.getByText(/create content/i)).toBeInTheDocument();
    });
  });
});
