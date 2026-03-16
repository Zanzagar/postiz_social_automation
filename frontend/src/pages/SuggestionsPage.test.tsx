import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SuggestionsPage } from "./SuggestionsPage";

vi.mock("@/lib/api", () => ({
  api: {
    getSuggestions: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetSuggestions = vi.mocked(api.getSuggestions);

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
    mockGetSuggestions.mockResolvedValue([
      {
        suggested_date: "2026-03-20",
        content_idea: "Spring planting ceremony photos",
        suggested_pillar: "farm",
        rationale: "Seasonal relevance",
        media_suggestion: "Photos of the fields",
        status: "pending",
      },
    ]);
    renderSuggestions();
    await waitFor(() => {
      expect(screen.getByText(/spring planting/i)).toBeInTheDocument();
      expect(screen.getByText(/seasonal relevance/i)).toBeInTheDocument();
    });
  });

  it("shows empty state", async () => {
    mockGetSuggestions.mockResolvedValue([]);
    renderSuggestions();
    await waitFor(() => {
      expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
    });
  });
});
