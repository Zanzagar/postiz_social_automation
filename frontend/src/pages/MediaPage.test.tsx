import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MediaPage } from "./MediaPage";
import type {
  MediaBrowseParams,
  MediaBrowseResponse,
  MediaDetailResponse,
  MediaItem,
  MediaUploadResponse,
  Pillar,
} from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getMedia: vi.fn(),
    getMediaDetail: vi.fn(),
    updateMedia: vi.fn(),
    updateMediaTags: vi.fn(),
    generateMediaMeta: vi.fn(),
    getAdaptedVersions: vi.fn(),
    adaptMedia: vi.fn(),
    deleteMedia: vi.fn(),
    uploadMediaFile: vi.fn(),
    importMediaUrl: vi.fn(),
    getPillars: vi.fn(),
    browseDrive: vi.fn(),
    importFromDrive: vi.fn(),
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

const mockGetMedia = vi.mocked(api.getMedia);
const mockGetMediaDetail = vi.mocked(api.getMediaDetail);
const mockUpdateMedia = vi.mocked(api.updateMedia);
const mockUpdateTags = vi.mocked(api.updateMediaTags);
const mockGenerateMeta = vi.mocked(api.generateMediaMeta);
const mockGetAdapted = vi.mocked(api.getAdaptedVersions);
const mockAdaptMedia = vi.mocked(api.adaptMedia);
const mockDeleteMedia = vi.mocked(api.deleteMedia);
const mockUpload = vi.mocked(api.uploadMediaFile);
const mockGetPillars = vi.mocked(api.getPillars);

// Frozen "today" — Wednesday, July 15 2026.
const TODAY = new Date("2026-07-15T09:00:00");

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

const VID: MediaItem = {
  id: 2,
  filename: "milking.mp4",
  local_path: "media/vid.mp4",
  thumbnail_path: null,
  mime_type: "video/mp4",
  width: null,
  height: null,
  file_size: 9876543,
  pillar: null,
  source: "drive",
  usage_count: 0,
  avg_engagement: 0,
  created_at: "2026-07-05T10:00:00",
  alt_text: null,
  default_caption: null,
  season: null,
  original_url: null,
};

const BROWSE: MediaBrowseResponse = {
  items: [IMG, VID],
  total: 2,
  page: 1,
  per_page: 30,
  total_pages: 1,
  storage_used_bytes: 1572864, // 1.5 MB
};

const DETAIL: MediaDetailResponse = {
  media: IMG,
  tags: [{ id: 1, tag: "cows", confidence: 0.9, source: "ai" }],
  usage: [
    {
      content_row_id: 12,
      date: "2026-07-10T12:00:00",
      status: "posted",
      pillar: "Cow Life",
    },
  ],
  performance: [],
};

const PILLARS: Pillar[] = [
  {
    id: 1,
    name: "Cow Life",
    description: null,
    color: null,
    target: null,
    is_active: true,
    sort_order: 0,
  },
];

const UPLOAD_RES: MediaUploadResponse = {
  id: 99,
  filename: "new-photo.png",
  local_path: "media/new.png",
  thumbnail_path: "media/thumbnails/thumb_new.jpg",
  postiz_media_id: null,
  mime_type: "image/png",
  width: 800,
  height: 600,
  file_size: 1234,
  source: "upload",
  original_url: null,
  tags: [],
  alt_text: null,
  season: null,
};

function seedMocks() {
  mockGetMedia.mockResolvedValue(BROWSE);
  mockGetPillars.mockResolvedValue(PILLARS);
  mockGetMediaDetail.mockImplementation((id: number) =>
    Promise.resolve(
      id === 1
        ? DETAIL
        : {
            media: { ...IMG, id, filename: `media-${id}.jpg`, alt_text: null },
            tags: [],
            usage: [],
            performance: [],
          },
    ),
  );
  mockGetAdapted.mockResolvedValue({
    adapted: [
      {
        id: 7,
        platform: "instagram",
        format: "post",
        adapted_path: "media/adapted/1_instagram_post.jpg",
        width: 1080,
        height: 1080,
        has_text_overlay: false,
        created_at: "2026-07-02T00:00:00",
      },
    ],
  });
  mockUpdateMedia.mockResolvedValue(IMG);
  mockUpdateTags.mockResolvedValue({ tags: [] });
  mockGenerateMeta.mockResolvedValue({
    alt_text: "Fresh alt from Claude",
    season: "summer",
    suggested_tags: [{ tag: "pasture", confidence: 0.8 }],
  });
  mockAdaptMedia.mockResolvedValue({ adapted: [] });
  mockDeleteMedia.mockResolvedValue({ deleted: true, id: 1 });
  mockUpload.mockResolvedValue(UPLOAD_RES);
}

function CreateProbe() {
  const location = useLocation();
  return <div>create-probe:{location.search}</div>;
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<MediaPage />} />
          <Route path="/create" element={<CreateProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Render, wait for the grid, select the image tile, wait for the inspector. */
async function openInspector(user: ReturnType<typeof userEvent.setup>) {
  renderPage();
  await screen.findByText("lakshmi-calf.jpg");
  await user.click(screen.getByRole("button", { name: /a cow with her calf/i }));
  await screen.findByText("Filename");
}

describe("MediaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(TODAY);
    seedMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the header, the grid, and REEL / NO ALT badges", async () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Images, reels, and stills" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Drop photos or videos here, or paste from clipboard"),
    ).toBeInTheDocument();
    await screen.findByText("lakshmi-calf.jpg");
    // image thumbnail URL: "/" + thumbnail_path (already media/-prefixed)
    expect(screen.getByRole("img", { name: "A cow with her calf" })).toHaveAttribute(
      "src",
      "/media/thumbnails/thumb_abc.jpg",
    );
    // video: REEL badge (no invented duration) + NO ALT status badge
    expect(screen.getByText("REEL")).toBeInTheDocument();
    const noAlt = screen.getByText("NO ALT");
    expect(noAlt).toHaveAttribute("role", "status");
    expect(mockGetMedia).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, per_page: 30, sort: "date" }),
    );
    // nothing selected yet — the aside shows the calm empty state
    expect(
      screen.getByText("Select an item to edit its details."),
    ).toBeInTheDocument();
  });

  it("shows the empty-library state when nothing exists and no filters are set", async () => {
    mockGetMedia.mockResolvedValue({
      ...BROWSE,
      items: [],
      total: 0,
      storage_used_bytes: 0,
    });
    renderPage();
    await screen.findByText("No media yet");
    expect(
      screen.getByText("Drop a photo above or import from Drive to start the library."),
    ).toBeInTheDocument();
  });

  it("shows the no-results state with active filters and clears them", async () => {
    mockGetMedia.mockImplementation((p?: MediaBrowseParams) =>
      Promise.resolve(p?.media_type ? { ...BROWSE, items: [], total: 0 } : BROWSE),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("lakshmi-calf.jpg");
    await user.click(screen.getByRole("button", { name: "Photos" }));
    await screen.findByText("Nothing matches those filters");
    expect(mockGetMedia).toHaveBeenLastCalledWith(
      expect.objectContaining({ media_type: "image", page: 1 }),
    );
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await screen.findByText("lakshmi-calf.jpg");
    const last = mockGetMedia.mock.calls.at(-1)?.[0];
    expect(last?.media_type).toBeUndefined();
  });

  it("debounces the search box into the server-backed q param", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("lakshmi-calf.jpg");
    await user.type(screen.getByRole("searchbox", { name: "Search media" }), "calf");
    await waitFor(() =>
      expect(mockGetMedia).toHaveBeenCalledWith(
        expect.objectContaining({ q: "calf", page: 1 }),
      ),
    );
  });

  it("drives media_type and untagged params from the type chips", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("lakshmi-calf.jpg");
    await user.click(screen.getByRole("button", { name: "Videos" }));
    await waitFor(() =>
      expect(mockGetMedia).toHaveBeenLastCalledWith(
        expect.objectContaining({ media_type: "video" }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Untagged" }));
    await waitFor(() =>
      expect(mockGetMedia).toHaveBeenLastCalledWith(
        expect.objectContaining({ untagged: true }),
      ),
    );
    // single-select: switching chips replaces, never stacks
    const last = mockGetMedia.mock.calls.at(-1)?.[0];
    expect(last?.media_type).toBeUndefined();
  });

  it("renders the honest storage caption from storage_used_bytes (no fake quota)", async () => {
    renderPage();
    await screen.findByText("2 items · 1.5 MB used");
    expect(screen.getByPlaceholderText("Search 2 items")).toBeInTheDocument();
    expect(screen.queryByText(/of 10 GB/i)).not.toBeInTheDocument();
  });

  it("selecting a tile opens the inspector with detail fields", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    // filename appears in the grid label AND the inspector value
    expect(screen.getAllByText("lakshmi-calf.jpg").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByLabelText("Alt-text")).toHaveValue("A cow with her calf");
    expect(screen.getByText("Screen-reader friendly · 19 chars")).toBeInTheDocument();
    expect(screen.getByLabelText("Caption (default)")).toHaveValue(
      "Morning at the barn",
    );
    expect(screen.getByText("cows")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Season" })).toBeInTheDocument();
    // usage is real data; toggle the compact list
    expect(screen.getByText("1 post")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "see" }));
    expect(screen.getByText("#12")).toBeInTheDocument();
    // metadata card — real fields only
    expect(screen.getByText("Jul 1, 2026")).toBeInTheDocument();
    expect(screen.getByText("2048 × 1536")).toBeInTheDocument();
    expect(screen.getByText("337.6 KB")).toBeInTheDocument();
  });

  it("saves alt-text on blur via updateMedia", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    const alt = screen.getByLabelText("Alt-text");
    await user.clear(alt);
    await user.type(alt, "Two cows at dawn");
    await user.tab();
    await waitFor(() =>
      expect(mockUpdateMedia).toHaveBeenCalledWith(1, { alt_text: "Two cows at dawn" }),
    );
  });

  it("adds and removes tags via updateMediaTags", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    await user.type(screen.getByLabelText("Add tag"), "barn{Enter}");
    await waitFor(() => expect(mockUpdateTags).toHaveBeenCalledWith(1, ["barn"], []));
    await user.click(screen.getByRole("button", { name: "Remove cows" }));
    await waitFor(() => expect(mockUpdateTags).toHaveBeenCalledWith(1, [], ["cows"]));
  });

  it("regenerates metadata with Claude and offers additive tag suggestions", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    await user.click(screen.getByRole("button", { name: /regenerate with claude/i }));
    await waitFor(() => expect(mockGenerateMeta).toHaveBeenCalledWith(1));
    await screen.findByText("Claude suggests:");
    expect(screen.getByLabelText("Alt-text")).toHaveValue("Fresh alt from Claude");
    await user.click(screen.getByRole("button", { name: "+ pasture" }));
    await waitFor(() => expect(mockUpdateTags).toHaveBeenCalledWith(1, ["pasture"], []));
  });

  it("lists platform versions and generates exactly the chosen combos", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    // existing adapted version row (honest dims, View link)
    await screen.findByText("Instagram · Post");
    expect(screen.getByText("1080 × 1080")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument();
    expect(
      screen.getByText(/preview is approximate — final crop & compression/i),
    ).toBeInTheDocument();
    // open the picker — all 6 combos preselected
    await user.click(screen.getByRole("button", { name: "Generate crops" }));
    for (const name of [
      "Instagram · Post 1:1",
      "Instagram · Story 9:16",
      "Facebook · Post 1.91:1",
      "Facebook · Story 9:16",
      "TikTok · Story 9:16",
      "LinkedIn · Post 1.91:1",
    ]) {
      expect(screen.getByRole("button", { name })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    }
    // keep only the two Instagram combos
    await user.click(screen.getByRole("button", { name: "Facebook · Post 1.91:1" }));
    await user.click(screen.getByRole("button", { name: "Facebook · Story 9:16" }));
    await user.click(screen.getByRole("button", { name: "TikTok · Story 9:16" }));
    await user.click(screen.getByRole("button", { name: "LinkedIn · Post 1.91:1" }));
    await user.click(screen.getByRole("button", { name: "Generate 2" }));
    await waitFor(() =>
      expect(mockAdaptMedia).toHaveBeenCalledWith(1, ["instagram"], ["post", "story"]),
    );
    expect(mockAdaptMedia).toHaveBeenCalledTimes(1);
  });

  it("navigates to /create?media={id} from Use in a draft", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    await user.click(screen.getByRole("button", { name: "Use in a draft" }));
    await screen.findByText("create-probe:?media=1");
  });

  it("deletes only after the two-step inline confirm", async () => {
    const user = userEvent.setup();
    await openInspector(user);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(mockDeleteMedia).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Really delete?" }));
    await waitFor(() => expect(mockDeleteMedia).toHaveBeenCalledWith(1));
    await screen.findByText("Select an item to edit its details.");
  });

  it("uploads via the file input and shows the Claude banner while in flight", async () => {
    let resolveUpload!: (v: MediaUploadResponse) => void;
    mockUpload.mockImplementation(
      () =>
        new Promise<MediaUploadResponse>((resolve) => {
          resolveUpload = resolve;
        }),
    );
    renderPage();
    await screen.findByText("lakshmi-calf.jpg");
    const input = screen.getByLabelText("Upload files");
    const file = new File(["x"], "new-photo.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });
    await screen.findByText(
      "Claude is generating alt-text, tags, and a season guess for your upload.",
    );
    // indeterminate row — no fake percentages, no dead cancel button
    expect(screen.getByText("Uploading & analyzing…")).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Uploading new-photo.png" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
    expect(mockUpload).toHaveBeenCalledWith(file);
    resolveUpload(UPLOAD_RES);
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Added new-photo.png"),
    );
    await waitFor(() =>
      expect(
        screen.queryByText(/claude is generating alt-text/i),
      ).not.toBeInTheDocument(),
    );
  });

  it("rejects GIFs and oversized files client-side before any API call", async () => {
    renderPage();
    await screen.findByText("lakshmi-calf.jpg");
    const input = screen.getByLabelText("Upload files");
    const gif = new File(["x"], "dance.gif", { type: "image/gif" });
    fireEvent.change(input, { target: { files: [gif] } });
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("GIF")),
    );
    const big = new File(["x"], "huge.jpg", { type: "image/jpeg" });
    Object.defineProperty(big, "size", { value: 101 * 1024 * 1024 });
    fireEvent.change(input, { target: { files: [big] } });
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("100 MB")),
    );
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("opens the same inspector in a GVSheet below the lg breakpoint", async () => {
    const originalWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", {
      value: 800,
      configurable: true,
      writable: true,
    });
    try {
      const user = userEvent.setup();
      renderPage();
      await screen.findByText("lakshmi-calf.jpg");
      await user.click(screen.getByRole("button", { name: /a cow with her calf/i }));
      const dialog = await screen.findByRole("dialog", { name: "Media details" });
      expect(await within(dialog).findByLabelText("Alt-text")).toHaveValue(
        "A cow with her calf",
      );
    } finally {
      Object.defineProperty(window, "innerWidth", {
        value: originalWidth,
        configurable: true,
        writable: true,
      });
    }
  });
});
