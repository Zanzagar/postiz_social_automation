import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SettingsPage } from "./SettingsPage";

vi.mock("@/lib/api", () => ({
  api: {
    getPublishConfig: vi.fn(),
    updatePublishConfig: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetConfig = vi.mocked(api.getPublishConfig);
const mockUpdateConfig = vi.mocked(api.updatePublishConfig);

const sampleConfig = {
  platforms: [
    { platform: "facebook", enabled: true, delay_hours: 2, pillar_overrides: {} },
    { platform: "instagram", enabled: false, delay_hours: 4, pillar_overrides: {} },
  ],
};

function renderSettings() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading state", () => {
    mockGetConfig.mockReturnValue(new Promise(() => {}));
    renderSettings();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders platform publish configs", async () => {
    mockGetConfig.mockResolvedValue(sampleConfig);
    renderSettings();
    await waitFor(() => {
      expect(screen.getByText(/facebook/i)).toBeInTheDocument();
      expect(screen.getByText(/instagram/i)).toBeInTheDocument();
    });
  });

  it("shows enabled/disabled state per platform", async () => {
    mockGetConfig.mockResolvedValue(sampleConfig);
    renderSettings();
    await waitFor(() => {
      expect(screen.getByLabelText(/facebook.*enabled/i)).toBeChecked();
      expect(screen.getByLabelText(/instagram.*enabled/i)).not.toBeChecked();
    });
  });

  it("saves config when save button clicked", async () => {
    const user = userEvent.setup();
    mockGetConfig.mockResolvedValue(sampleConfig);
    mockUpdateConfig.mockResolvedValue(sampleConfig);
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText(/facebook/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockUpdateConfig).toHaveBeenCalled();
    });
  });
});
