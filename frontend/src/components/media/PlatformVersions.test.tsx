import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformVersions } from "./PlatformVersions";
import type { MediaItem } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getAdaptedVersions: vi.fn(),
    adaptMedia: vi.fn(),
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
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { api } from "@/lib/api";

const mockGetAdapted = vi.mocked(api.getAdaptedVersions);
const mockAdaptMedia = vi.mocked(api.adaptMedia);

const IMG: MediaItem = {
  id: 1,
  filename: "lakshmi-calf.jpg",
  local_path: "media/abc.jpg",
  thumbnail_path: "media/thumbnails/thumb_abc.jpg",
  mime_type: "image/jpeg",
  width: 2048,
  height: 1536,
  file_size: 345678,
  pillar: "Cow Life",
  source: "upload",
  usage_count: 0,
  avg_engagement: 0,
  created_at: "2026-07-01T10:00:00",
  alt_text: "A cow with her calf",
  default_caption: null,
  season: null,
  original_url: null,
};

function renderVersions() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PlatformVersions media={IMG} />
    </QueryClientProvider>,
  );
}

describe("PlatformVersions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetAdapted.mockResolvedValue({ adapted: [] });
  });

  it("refetches adapted versions even when generation fails mid-sequence", async () => {
    // First platform succeeds, second fails — some crops WERE created.
    mockAdaptMedia
      .mockResolvedValueOnce({ adapted: [] })
      .mockRejectedValueOnce(new Error("disk full"));
    const user = userEvent.setup();
    renderVersions();

    await screen.findByText(/no platform versions yet/i);
    expect(mockGetAdapted).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Generate crops" }));
    await user.click(screen.getByRole("button", { name: "Generate 6" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("disk full");
    // onSettled invalidation refetches so partial successes still render.
    await waitFor(() => expect(mockGetAdapted).toHaveBeenCalledTimes(2));
  });
});
