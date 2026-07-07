import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DraftsPage } from "./DraftsPage";
import type { ContentRow } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getDrafts: vi.fn(),
    approveDraft: vi.fn(),
    editDraft: vi.fn(),
    iterate: vi.fn(),
    getIterations: vi.fn(),
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

import { api } from "@/lib/api";
const mockGetDrafts = vi.mocked(api.getDrafts);
const mockApproveDraft = vi.mocked(api.approveDraft);

const sampleDrafts: ContentRow[] = [
  {
    row_number: 2,
    date: "2026-03-17",
    content_pillar: "spiritual",
    raw_text: "Morning meditation at the temple",
    media_url: null,
    platforms: { instagram: true, facebook: true },
    status: "draft",
    captions: { instagram: "IG caption for meditation", facebook: "FB caption" },
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "manual",
    auto_publish_at: null,
    require_review: false,
    held_at: null,
    alt_text: null,
  },
  {
    row_number: 3,
    date: "2026-03-18",
    content_pillar: "farm",
    raw_text: "Cow protection update",
    media_url: "https://drive.google.com/file/abc",
    platforms: { instagram: true },
    status: "draft",
    captions: { instagram: "IG caption for cows" },
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "manual",
    auto_publish_at: null,
    require_review: false,
    held_at: null,
    alt_text: null,
  },
];

function renderDrafts() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DraftsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DraftsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockGetDrafts.mockReturnValue(new Promise(() => {}));
    renderDrafts();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows empty state when no drafts", async () => {
    mockGetDrafts.mockResolvedValue([]);
    renderDrafts();
    await waitFor(() => {
      expect(screen.getByText(/all caught up/i)).toBeInTheDocument();
    });
  });

  it("renders draft cards", async () => {
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();
    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
      expect(screen.getByText(/cow protection/i)).toBeInTheDocument();
    });
  });

  it("select all toggles all drafts", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
    });

    const selectAll = screen.getByLabelText(/select all/i);
    await user.click(selectAll);

    // Batch actions bar should appear
    expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
  });

  it("approve button calls API for selected drafts", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    mockApproveDraft.mockResolvedValue({ success: true, postiz_ids: ["p1"] });
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
    });

    // Select all then approve
    await user.click(screen.getByLabelText(/select all/i));
    await user.click(screen.getByRole("button", { name: /approve/i }));

    await waitFor(() => {
      expect(mockApproveDraft).toHaveBeenCalledTimes(2);
    });
  });

  // --- ContentEditor modal integration ---

  it("opens ContentEditor in refine mode when draft card is clicked", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    vi.mocked(api.getIterations).mockResolvedValue([]);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
    });

    // Click the draft text to open editor
    await user.click(screen.getByText(/morning meditation/i));

    await waitFor(() => {
      expect(screen.getByText(/refine content/i)).toBeInTheDocument();
    });
  });

  it("closes ContentEditor modal and refreshes drafts on save", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    vi.mocked(api.getIterations).mockResolvedValue([]);
    vi.mocked(api.editDraft).mockResolvedValue(sampleDrafts[0]);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByText(/morning meditation/i)).toBeInTheDocument();
    });

    // Open editor
    await user.click(screen.getByText(/morning meditation/i));

    await waitFor(() => {
      expect(screen.getByText(/refine content/i)).toBeInTheDocument();
    });

    // Close via the close buttons (footer one)
    const closeButtons = screen.getAllByRole("button", { name: /close/i });
    await user.click(closeButtons[closeButtons.length - 1]);

    await waitFor(() => {
      expect(screen.queryByText(/refine content/i)).not.toBeInTheDocument();
    });
  });
});
