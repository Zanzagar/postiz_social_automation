import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { HealthPage } from "./HealthPage";

vi.mock("@/lib/api", () => ({
  api: {
    getHealth: vi.fn(),
    getIntegrations: vi.fn(),
    getMediaHealth: vi.fn(),
    mediaCleanup: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetHealth = vi.mocked(api.getHealth);
const mockGetIntegrations = vi.mocked(api.getIntegrations);
const mockGetMediaHealth = vi.mocked(api.getMediaHealth);
const mockMediaCleanup = vi.mocked(api.mediaCleanup);

const MEDIA_OK = {
  total: 12,
  healthy: 9,
  drive_refs: 4,
  missing_file: [],
  missing_thumb: [],
  orphan_files: 0,
};

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

function seedHealthy() {
  mockGetHealth.mockResolvedValue({ services: [], errors: [] });
  mockGetIntegrations.mockResolvedValue([]);
  mockGetMediaHealth.mockResolvedValue(MEDIA_OK);
}

describe("HealthPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the Pasture header and a skeleton loading state", () => {
    mockGetHealth.mockReturnValue(new Promise(() => {}));
    mockGetIntegrations.mockReturnValue(new Promise(() => {}));
    mockGetMediaHealth.mockReturnValue(new Promise(() => {}));
    renderHealth();
    expect(screen.getByRole("heading", { name: "Health" })).toBeInTheDocument();
    expect(screen.getByText("Systems")).toBeInTheDocument();
    expect(
      screen.getByRole("status", { name: "Loading health" }),
    ).toBeInTheDocument();
  });

  it("maps backend ok/error and legacy statuses onto Healthy/Error/Degraded", async () => {
    seedHealthy();
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "postiz", status: "ok", message: "Reachable", last_checked: "2026-07-16T09:00:00Z" },
        { name: "claude", status: "error", message: "CLI not found", last_checked: "2026-07-16T09:00:00Z" },
        { name: "sheets", status: "degraded", message: "Slow responses", last_checked: "2026-07-16T09:00:00Z" },
        { name: "oauth", status: "unhealthy", message: "Token expired", last_checked: "2026-07-16T09:00:00Z" },
        { name: "Custom Service", status: "healthy", message: "Fine", last_checked: "2026-07-16T09:00:00Z" },
      ],
      errors: [],
    });
    renderHealth();
    const services = within(
      await screen.findByRole("region", { name: "Services" }),
    );
    expect(services.getAllByText("Healthy")).toHaveLength(2);
    expect(services.getAllByText("Error")).toHaveLength(2);
    expect(services.getByText("Degraded")).toBeInTheDocument();
    // raw backend statuses never reach the screen
    expect(services.queryByText("ok")).not.toBeInTheDocument();
    expect(services.queryByText("unhealthy")).not.toBeInTheDocument();
    // messages stay visible
    expect(services.getByText("CLI not found")).toBeInTheDocument();
    expect(services.getByText("Slow responses")).toBeInTheDocument();
  });

  it("shows friendly service names with a raw-name fallback", async () => {
    seedHealthy();
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "oauth", status: "ok", message: "Token valid", last_checked: "" },
        { name: "postiz", status: "ok", message: "Reachable", last_checked: "" },
        { name: "mystery", status: "ok", message: "???", last_checked: "" },
      ],
      errors: [],
    });
    renderHealth();
    const services = within(
      await screen.findByRole("region", { name: "Services" }),
    );
    expect(services.getByText("Claude login")).toBeInTheDocument();
    expect(services.getByText("Postiz")).toBeInTheDocument();
    expect(services.getByText("mystery")).toBeInTheDocument();
  });

  it("truncates long error messages behind a title attribute", async () => {
    seedHealthy();
    const blob =
      "HttpError 503 when requesting https://example.com/very/long/url returned " +
      "Service temporarily unavailable, please retry later — trace 123456789";
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "sheets", status: "error", message: blob, last_checked: "" },
      ],
      errors: [],
    });
    renderHealth();
    await screen.findByRole("region", { name: "Services" });
    const msg = screen.getByTitle(blob);
    expect(msg).toBeInTheDocument();
    expect(msg).toHaveClass("truncate");
  });

  it("shows an empty state when no services are configured", async () => {
    seedHealthy();
    renderHealth();
    expect(
      await screen.findByText("No services configured"),
    ).toBeInTheDocument();
  });

  it("renders the integrations list with platforms", async () => {
    seedHealthy();
    mockGetIntegrations.mockResolvedValue([
      { id: "ig1", platform: "instagram", name: "GV Instagram" },
      { id: "fb1", platform: "facebook", name: "GV Facebook" },
    ]);
    renderHealth();
    const card = within(
      await screen.findByRole("region", { name: "Postiz integrations" }),
    );
    expect(card.getByText("GV Instagram")).toBeInTheDocument();
    expect(card.getByText("GV Facebook")).toBeInTheDocument();
    expect(card.getByText("instagram")).toBeInTheDocument();
    expect(card.getByText("facebook")).toBeInTheDocument();
  });

  it("shows an empty state when no integrations exist", async () => {
    seedHealthy();
    renderHealth();
    expect(
      await screen.findByText("No Postiz integrations found"),
    ).toBeInTheDocument();
  });

  it("keeps all media catalog stats and the in-sync state", async () => {
    seedHealthy();
    renderHealth();
    const card = within(
      await screen.findByRole("region", { name: "Media catalog" }),
    );
    expect(card.getByText("12")).toBeInTheDocument(); // total
    expect(card.getByText("9")).toBeInTheDocument(); // healthy
    expect(card.getByText("4")).toBeInTheDocument(); // drive refs
    expect(card.getByText("3")).toBeInTheDocument(); // local files
    expect(card.getByText("Total items")).toBeInTheDocument();
    expect(card.getByText("Healthy")).toBeInTheDocument();
    expect(card.getByText("Drive refs")).toBeInTheDocument();
    expect(card.getByText("Local files")).toBeInTheDocument();
    expect(
      card.getByText(/all media files in sync — no issues detected/i),
    ).toBeInTheDocument();
    expect(
      card.queryByRole("button", { name: /clean up/i }),
    ).not.toBeInTheDocument();
  });

  it("lists media issues and runs cleanup", async () => {
    seedHealthy();
    mockGetMediaHealth.mockResolvedValue({
      total: 10,
      healthy: 6,
      drive_refs: 2,
      missing_file: [{ id: 1, filename: "a.jpg" }],
      missing_thumb: [
        { id: 2, filename: "b.jpg" },
        { id: 3, filename: "c.jpg" },
      ],
      orphan_files: 5,
    });
    mockMediaCleanup.mockResolvedValue({ removed_entries: 1, removed_orphans: 5 });
    const user = userEvent.setup();
    renderHealth();
    const card = within(
      await screen.findByRole("region", { name: "Media catalog" }),
    );
    expect(
      card.getByText("1 DB entries with missing files"),
    ).toBeInTheDocument();
    expect(card.getByText("2 missing thumbnails")).toBeInTheDocument();
    expect(card.getByText("5 orphaned files on disk")).toBeInTheDocument();
    await user.click(card.getByRole("button", { name: /clean up/i }));
    await waitFor(() =>
      expect(mockMediaCleanup).toHaveBeenCalledWith(true, true),
    );
    expect(
      await card.findByText(/cleaned up 1 entries and 5 orphan files/i),
    ).toBeInTheDocument();
  });
});
