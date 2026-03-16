import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";

// Mock the hook so we control data without network calls
vi.mock("@/hooks/useDashboardData", () => ({
  useDashboardData: vi.fn(),
}));

import { useDashboardData } from "@/hooks/useDashboardData";
const mockUseDashboard = vi.mocked(useDashboardData);

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

const baseData = {
  pendingCount: 3,
  scheduledThisWeek: 5,
  postedCount: 12,
  calendarEntries: [],
  services: [
    { name: "Google Sheets", status: "healthy", message: "OK", last_checked: "2026-03-16T12:00:00Z" },
    { name: "Postiz", status: "healthy", message: "OK", last_checked: "2026-03-16T12:00:00Z" },
    { name: "Claude", status: "degraded", message: "Slow", last_checked: "2026-03-16T12:00:00Z" },
  ],
  isLoading: false,
  isError: false,
};

describe("DashboardPage", () => {
  it("shows loading skeleton when data is loading", () => {
    mockUseDashboard.mockReturnValue({ ...baseData, isLoading: true });
    renderDashboard();
    expect(screen.getAllByTestId("skeleton-card").length).toBeGreaterThanOrEqual(1);
  });

  it("displays stat cards with correct counts", () => {
    mockUseDashboard.mockReturnValue(baseData);
    renderDashboard();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("shows health service indicators", () => {
    mockUseDashboard.mockReturnValue(baseData);
    renderDashboard();
    expect(screen.getByText("Google Sheets")).toBeInTheDocument();
    expect(screen.getByText("Postiz")).toBeInTheDocument();
    expect(screen.getByText("Claude")).toBeInTheDocument();
  });

  it("shows quick create link", () => {
    mockUseDashboard.mockReturnValue(baseData);
    renderDashboard();
    const link = screen.getByRole("link", { name: /create content/i });
    expect(link).toHaveAttribute("href", "/create");
  });

  it("renders health status colors correctly", () => {
    mockUseDashboard.mockReturnValue(baseData);
    renderDashboard();
    const healthSection = screen.getByTestId("health-status");
    // healthy = green dot, degraded = yellow dot
    const dots = healthSection.querySelectorAll("[data-status]");
    const statuses = Array.from(dots).map((d) => d.getAttribute("data-status"));
    expect(statuses).toContain("healthy");
    expect(statuses).toContain("degraded");
  });
});
