import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DraftsPage } from "./DraftsPage";
import type { ContentRow } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getDrafts: vi.fn(),
    getPillars: vi.fn(),
    approveDraft: vi.fn(),
    editDraft: vi.fn(),
    holdContent: vi.fn(),
    resumeContent: vi.fn(),
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

vi.mock("@/components/content/ContentEditorSheet", () => ({
  ContentEditorSheet: ({
    rowId,
    mode,
    onClose,
  }: {
    rowId: number | null;
    mode: string;
    onClose: () => void;
  }) =>
    rowId === null ? null : (
      <div data-testid="editor-sheet">
        Editing row {rowId} in {mode} mode
        <button onClick={onClose}>Close editor</button>
      </div>
    ),
}));

import { api } from "@/lib/api";
import { toast } from "sonner";

const mockGetDrafts = vi.mocked(api.getDrafts);
const mockGetPillars = vi.mocked(api.getPillars);
const mockApproveDraft = vi.mocked(api.approveDraft);
const mockHoldContent = vi.mocked(api.holdContent);
const mockResumeContent = vi.mocked(api.resumeContent);

function row(overrides: Partial<ContentRow>): ContentRow {
  return {
    row_number: 1,
    date: "2026-07-08",
    content_pillar: "Cow Life",
    raw_text: "Sample text",
    media_url: null,
    platforms: { instagram: true },
    status: "draft",
    captions: {},
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "manual",
    auto_publish_at: null,
    require_review: false,
    held_at: null,
    alt_text: null,
    ...overrides,
  };
}

const sampleDrafts: ContentRow[] = [
  row({
    row_number: 2,
    date: "2026-07-08",
    content_pillar: "Cow Life",
    raw_text: "Tabby found the sweet clover patch\nGolden hour in the pasture.",
    platforms: { instagram: true, facebook: true },
    status: "pending_approval",
  }),
  row({
    row_number: 3,
    date: "2026-07-09",
    content_pillar: "Farm Ops",
    raw_text: "Dennis inspects the new fence line",
    status: "draft",
  }),
  row({
    row_number: 4,
    date: "2026-07-06",
    content_pillar: "Community",
    raw_text: "Sparkle's harvest reel drops today",
    status: "approved",
    auto_publish_at: "2026-07-06T14:00:00",
  }),
  row({
    row_number: 5,
    date: "2026-07-01",
    content_pillar: "Cow Life",
    raw_text: "Daring Denise leads the evening walk",
    status: "posted",
    posted_at: "2026-07-01T18:00:00",
  }),
  row({
    row_number: 6,
    date: "2026-07-06",
    content_pillar: "Farm Ops",
    raw_text: "Brisham naps by the barn",
    status: "approved",
    auto_publish_at: "2026-07-06T15:30:00",
    held_at: "2026-07-06T11:00:00",
  }),
];

function renderDrafts() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<DraftsPage />} />
          <Route path="/create" element={<div>Create page stub</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DraftsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Freeze the clock so countdown labels are deterministic (never expires).
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-07-06T12:00:00"));
    mockGetPillars.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows loading skeletons", () => {
    mockGetDrafts.mockReturnValue(new Promise(() => {}));
    renderDrafts();
    expect(
      screen.getByRole("status", { name: /loading drafts/i }),
    ).toBeInTheDocument();
  });

  it("shows the empty workbench state with a Start a post action", async () => {
    mockGetDrafts.mockResolvedValue([]);
    renderDrafts();
    await waitFor(() => {
      expect(
        screen.getByText(/nothing on the workbench yet/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /start a post/i }),
    ).toBeInTheDocument();
  });

  it("renders header, rows, and live filter counts", async () => {
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /tabby found the sweet clover/i })).toBeInTheDocument();
    });
    expect(screen.getByText("The workbench")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /dennis inspects the new fence/i })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /^all/i })).toHaveTextContent("5");
    expect(screen.getByRole("button", { name: /needs review/i })).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: /in progress/i })).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: /scheduled/i })).toHaveTextContent("2");
    expect(screen.getByRole("button", { name: /posted/i })).toHaveTextContent("1");
  });

  it("filters rows by status when a pill is clicked", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /tabby found the sweet clover/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /posted/i }));

    expect(screen.getByRole("heading", { name: /daring denise leads the evening/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /tabby found the sweet clover/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /dennis inspects the new fence/i })).not.toBeInTheDocument();
  });

  it("opens the content editor sheet when a row is opened, and closes it", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /dennis inspects the new fence/i })).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /open dennis inspects the new fence line/i }),
    );

    expect(screen.getByTestId("editor-sheet")).toHaveTextContent(
      "Editing row 3 in refine mode",
    );

    await user.click(screen.getByRole("button", { name: /close editor/i }));
    expect(screen.queryByTestId("editor-sheet")).not.toBeInTheDocument();
  });

  it("shows the auto-publish countdown and holds via the API", async () => {
    const user = userEvent.setup();
    const heldSparkle = sampleDrafts.map((d) =>
      d.row_number === 4 ? { ...d, held_at: "2026-07-06T12:00:30" } : d,
    );
    mockGetDrafts
      .mockResolvedValueOnce(sampleDrafts)
      .mockResolvedValue(heldSparkle);
    mockHoldContent.mockResolvedValue(heldSparkle[2]);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByText("Releases 2:00 PM")).toBeInTheDocument();
    });
    expect(screen.getByText("in 2h 0m")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /pause and hold for review/i }),
    );

    await waitFor(() => {
      expect(mockHoldContent).toHaveBeenCalledWith(4);
    });
    // Sparkle's chip flips to held (Brisham's was already held).
    await waitFor(() => {
      expect(screen.getAllByText(/held for review/i)).toHaveLength(2);
    });
  });

  it("resumes a held post via the API", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    mockResumeContent.mockResolvedValue({
      ...sampleDrafts[4],
      held_at: null,
    });
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /brisham naps by the barn/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/held for review/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /resume auto-release/i }),
    );

    await waitFor(() => {
      expect(mockResumeContent).toHaveBeenCalledWith(6);
    });
  });

  it("batch approves selected needs-review rows", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    mockApproveDraft.mockResolvedValue({ success: true, postiz_ids: ["p1"] });
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /tabby found the sweet clover/i })).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("checkbox", { name: /select tabby found the sweet clover/i }),
    );
    expect(screen.getByText(/1 selected/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /approve 1/i }));

    await waitFor(() => {
      expect(mockApproveDraft).toHaveBeenCalledTimes(1);
      expect(mockApproveDraft).toHaveBeenCalledWith(2);
    });
    expect(toast.success).toHaveBeenCalled();
    // Bar disappears once everything approved
    await waitFor(() => {
      expect(screen.queryByText(/1 selected/i)).not.toBeInTheDocument();
    });
  });

  it("keeps failed rows selected and toasts on batch approve failure", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    mockApproveDraft.mockRejectedValue(new Error("boom"));
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /tabby found the sweet clover/i })).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("checkbox", { name: /select tabby found the sweet clover/i }),
    );
    await user.click(screen.getByRole("button", { name: /approve 1/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledTimes(1);
    });
    expect(toast.success).not.toHaveBeenCalled();
    // Failed row stays selected for retry
    expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
  });

  it("navigates to /create from the New draft button", async () => {
    const user = userEvent.setup();
    mockGetDrafts.mockResolvedValue(sampleDrafts);
    renderDrafts();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /tabby found the sweet clover/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /new draft/i }));
    await waitFor(() => {
      expect(screen.getByText("Create page stub")).toBeInTheDocument();
    });
    expect(screen.queryByText("The workbench")).not.toBeInTheDocument();
  });
});
