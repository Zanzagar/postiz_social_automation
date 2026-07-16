import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MediaInspector } from "./MediaInspector";
import type { MediaDetailResponse, MediaItem } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getMediaDetail: vi.fn(),
    updateMedia: vi.fn(),
    updateMediaTags: vi.fn(),
    generateMediaMeta: vi.fn(),
    getAdaptedVersions: vi.fn(),
    adaptMedia: vi.fn(),
    deleteMedia: vi.fn(),
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
import { toast } from "sonner";

const mockGetMediaDetail = vi.mocked(api.getMediaDetail);
const mockUpdateMedia = vi.mocked(api.updateMedia);
const mockUpdateTags = vi.mocked(api.updateMediaTags);
const mockGetAdapted = vi.mocked(api.getAdaptedVersions);

// Radix Select needs these DOM APIs that jsdom doesn't implement.
window.HTMLElement.prototype.scrollIntoView = vi.fn();
window.HTMLElement.prototype.hasPointerCapture = vi.fn(() => false);
window.HTMLElement.prototype.setPointerCapture = vi.fn();
window.HTMLElement.prototype.releasePointerCapture = vi.fn();
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

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
  default_caption: "Morning at the barn",
  season: "summer",
  original_url: null,
};

const DETAIL: MediaDetailResponse = {
  media: IMG,
  tags: [{ id: 1, tag: "cows", confidence: 0.9, source: "ai" }],
  usage: [],
  performance: [],
};

function renderInspector(mediaId = 1) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MediaInspector mediaId={mediaId} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MediaInspector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetMediaDetail.mockResolvedValue(DETAIL);
    mockGetAdapted.mockResolvedValue({ adapted: [] });
    mockUpdateMedia.mockResolvedValue(IMG);
    mockUpdateTags.mockResolvedValue({ tags: [] });
  });

  it("shows an error state when the detail load fails, and Retry refetches", async () => {
    mockGetMediaDetail.mockRejectedValueOnce(new Error("boom"));
    const user = userEvent.setup();
    renderInspector();

    expect(
      await screen.findByText(
        "Couldn't load this item — it may have been deleted.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("Filename");
    expect(mockGetMediaDetail).toHaveBeenCalledTimes(2);
  });

  it("renders both chips (no duplicate keys) for two rapid optimistic tag adds", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    // Keep both mutations pending so both placeholders coexist in the cache.
    mockUpdateTags.mockImplementation(() => new Promise(() => {}));
    const user = userEvent.setup();
    renderInspector();
    await screen.findByText("Filename");

    const input = screen.getByLabelText("Add tag");
    await user.type(input, "barn{Enter}");
    await user.type(input, "hay{Enter}");

    expect(await screen.findByText("barn")).toBeInTheDocument();
    expect(screen.getByText("hay")).toBeInTheDocument();
    const duplicateKeyWarnings = consoleError.mock.calls.filter((call) =>
      String(call[0]).includes("same key"),
    );
    expect(duplicateKeyWarnings).toHaveLength(0);
    consoleError.mockRestore();
  });

  it("reverts the season select to the cached value when the PATCH fails", async () => {
    mockGetMediaDetail.mockResolvedValue({
      ...DETAIL,
      media: { ...IMG, season: null },
    });
    mockUpdateMedia.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderInspector();
    await screen.findByText("Filename");

    const trigger = screen.getByRole("combobox", { name: "Season" });
    expect(trigger).toHaveTextContent("Not set");

    await user.click(trigger);
    await user.click(await screen.findByRole("option", { name: "Spring" }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Couldn't save changes"),
    );
    // Rollback restored season=null in the cache — the controlled Select
    // must visually revert to the placeholder, not keep "Spring".
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Season" })).toHaveTextContent(
        "Not set",
      ),
    );
  });
});
