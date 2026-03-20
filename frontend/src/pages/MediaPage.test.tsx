import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MediaPage } from "./MediaPage";

// Mock API
vi.mock("@/lib/api", () => ({
  api: {
    getMedia: vi.fn(),
    getMediaDetail: vi.fn(),
    updateMediaTags: vi.fn(),
    deleteMedia: vi.fn(),
    getPillars: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockApi = vi.mocked(api);

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MediaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const sampleItems = [
  {
    id: 1,
    filename: "cow-photo.jpg",
    local_path: "media/abc123.jpg",
    thumbnail_path: "media/thumbnails/thumb_abc123.jpg",
    mime_type: "image/jpeg",
    width: 800,
    height: 600,
    file_size: 50000,
    pillar: "farm_life",
    source: "upload",
    usage_count: 3,
    avg_engagement: 0.85,
    created_at: "2026-03-15T10:00:00",
  },
  {
    id: 2,
    filename: "temple.jpg",
    local_path: "media/def456.jpg",
    thumbnail_path: "media/thumbnails/thumb_def456.jpg",
    mime_type: "image/jpeg",
    width: 1920,
    height: 1080,
    file_size: 120000,
    pillar: "spiritual_education",
    source: "import_url",
    usage_count: 0,
    avg_engagement: 0,
    created_at: "2026-03-16T10:00:00",
  },
];

const sampleBrowse = {
  items: sampleItems,
  total: 2,
  page: 1,
  per_page: 20,
  total_pages: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.getPillars.mockResolvedValue([]);
  mockApi.getMedia.mockResolvedValue(sampleBrowse);
});

describe("MediaPage", () => {
  it("renders media grid with items", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("cow-photo.jpg")).toBeInTheDocument();
      expect(screen.getByText("temple.jpg")).toBeInTheDocument();
    });
  });

  it("shows total count", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("2 items")).toBeInTheDocument();
    });
  });

  it("shows empty state when no items", async () => {
    mockApi.getMedia.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("No media found")).toBeInTheDocument();
    });
  });

  it("shows loading skeletons initially", () => {
    mockApi.getMedia.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("opens detail dialog on card click", async () => {
    mockApi.getMediaDetail.mockResolvedValue({
      media: sampleItems[0],
      tags: [
        { id: 1, tag: "cows", confidence: 0.95, source: "ai" },
        { id: 2, tag: "farm", confidence: 0.8, source: "ai" },
      ],
      usage: [],
      performance: [],
    });

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("cow-photo.jpg")).toBeInTheDocument();
    });

    await user.click(screen.getByText("cow-photo.jpg"));

    await waitFor(() => {
      expect(screen.getByText("cows")).toBeInTheDocument();
      expect(screen.getByText("farm")).toBeInTheDocument();
    });
  });

  it("shows pillar badges on cards", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("farm_life")).toBeInTheDocument();
      expect(screen.getByText("spiritual_education")).toBeInTheDocument();
    });
  });

  it("does not show pagination when single page", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("cow-photo.jpg")).toBeInTheDocument();
    });
    expect(screen.queryByText("Previous")).not.toBeInTheDocument();
    expect(screen.queryByText("Next")).not.toBeInTheDocument();
  });

  it("shows pagination when multiple pages", async () => {
    mockApi.getMedia.mockResolvedValue({
      ...sampleBrowse,
      total: 50,
      total_pages: 3,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Previous")).toBeInTheDocument();
      expect(screen.getByText("Next")).toBeInTheDocument();
      expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    });
  });
});
