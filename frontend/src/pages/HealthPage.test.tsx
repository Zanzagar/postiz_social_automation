import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { HealthPage } from "./HealthPage";

vi.mock("@/lib/api", () => ({
  api: {
    getHealth: vi.fn(),
    getIntegrations: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetHealth = vi.mocked(api.getHealth);
const mockGetIntegrations = vi.mocked(api.getIntegrations);

function renderHealth() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <HealthPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("HealthPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading state", () => {
    mockGetHealth.mockReturnValue(new Promise(() => {}));
    mockGetIntegrations.mockReturnValue(new Promise(() => {}));
    renderHealth();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders service health with status indicators", async () => {
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "Google Sheets", status: "healthy", message: "Connected", last_checked: "2026-03-16T12:00:00Z" },
        { name: "Postiz", status: "unhealthy", message: "Connection refused", last_checked: "2026-03-16T12:00:00Z" },
      ],
      errors: [],
    });
    mockGetIntegrations.mockResolvedValue([
      { id: "ig1", platform: "instagram", name: "GV Instagram" },
    ]);
    renderHealth();
    await waitFor(() => {
      expect(screen.getByText("Google Sheets")).toBeInTheDocument();
      expect(screen.getByText("Connected")).toBeInTheDocument();
      expect(screen.getByText("Connection refused")).toBeInTheDocument();
    });
  });

  it("renders integrations list", async () => {
    mockGetHealth.mockResolvedValue({ services: [], errors: [] });
    mockGetIntegrations.mockResolvedValue([
      { id: "ig1", platform: "instagram", name: "GV Instagram" },
      { id: "fb1", platform: "facebook", name: "GV Facebook" },
    ]);
    renderHealth();
    await waitFor(() => {
      expect(screen.getByText("GV Instagram")).toBeInTheDocument();
      expect(screen.getByText("GV Facebook")).toBeInTheDocument();
    });
  });
});
