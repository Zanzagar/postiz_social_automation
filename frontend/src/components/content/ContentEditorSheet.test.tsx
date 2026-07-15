import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ContentRow, IterationRecord } from "@/lib/api";

import { ContentEditorSheet } from "./ContentEditorSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/lib/api", () => ({
  api: {
    getContentRow: vi.fn(),
    getIterations: vi.fn(),
    getPillars: vi.fn(),
    iterate: vi.fn(),
    revertCaption: vi.fn(),
    deleteIteration: vi.fn(),
    editDraft: vi.fn(),
    approveDraft: vi.fn(),
    setRequireReview: vi.fn(),
    setAltText: vi.fn(),
    holdContent: vi.fn(),
    resumeContent: vi.fn(),
  },
  request: vi.fn(),
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

import { api, request } from "@/lib/api";

const mockGetContentRow = vi.mocked(api.getContentRow);
const mockGetIterations = vi.mocked(api.getIterations);
const mockGetPillars = vi.mocked(api.getPillars);
const mockIterate = vi.mocked(api.iterate);
const mockRevertCaption = vi.mocked(api.revertCaption);
const mockEditDraft = vi.mocked(api.editDraft);
const mockApproveDraft = vi.mocked(api.approveDraft);
const mockSetRequireReview = vi.mocked(api.setRequireReview);
const mockSetAltText = vi.mocked(api.setAltText);
const mockRequest = vi.mocked(request);

const baseRow: ContentRow = {
  row_number: 7,
  date: "2026-07-10",
  content_pillar: "Cow Life",
  raw_text:
    "Rain on the north pasture\nTabby and Dennis shelter under the walnut tree.",
  media_url: null,
  platforms: { instagram: true, facebook: true },
  status: "pending_approval",
  captions: {
    instagram:
      "Rain rolls in over the north pasture. Tabby and Dennis don't mind. #farmlife #gitavalley #rainyday #cows #sanctuary",
    facebook:
      "Rain on the pasture today — Tabby and Dennis found the walnut tree. #farmlife #gitavalley #cows",
  },
  feedback: null,
  postiz_ids: null,
  posted_at: null,
  error_msg: null,
  source: "manual",
  auto_publish_at: null,
  require_review: false,
  held_at: null,
  alt_text: null,
};

const iterationFixtures: IterationRecord[] = [
  {
    id: 11,
    content_row_id: 7,
    platform: "instagram",
    old_caption: null,
    new_caption: "First pass caption",
    refinement_instruction: null,
    mode: "generate",
    created_by: null,
    created_at: "2026-07-01T10:00:00Z",
  },
  {
    id: 12,
    content_row_id: 7,
    platform: "instagram",
    old_caption: "First pass caption",
    new_caption: "Warmer caption with calves",
    refinement_instruction: "warmer, mention the calves",
    mode: "refine",
    created_by: null,
    created_at: "2026-07-02T10:00:00Z",
  },
];

function renderSheet(
  props: Partial<React.ComponentProps<typeof ContentEditorSheet>> = {},
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();
  const onSaved = vi.fn();
  const utils = render(
    <QueryClientProvider client={qc}>
      <ContentEditorSheet
        rowId={7}
        mode="refine"
        onClose={onClose}
        onSaved={onSaved}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { ...utils, onClose, onSaved };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetContentRow.mockResolvedValue(baseRow);
  mockGetIterations.mockResolvedValue(iterationFixtures);
  mockGetPillars.mockResolvedValue([]);
});

describe("ContentEditorSheet — refine mode", () => {
  it("renders the row: title, mode badge, and a caption card per enabled platform", async () => {
    renderSheet();

    expect(await screen.findByText("Rain on the north pasture")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Refine")).toBeInTheDocument();

    // One caption card per enabled platform
    expect(screen.getByRole("textbox", { name: "Instagram caption" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Facebook caption" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Instagram caption" })).toHaveValue(
      baseRow.captions.instagram,
    );

    // Meta chips
    expect(screen.getByText("Cow Life")).toBeInTheDocument();
    expect(screen.getByText("2 platforms")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });

  it("iterates a single platform caption and refreshes history", async () => {
    const user = userEvent.setup();
    mockIterate.mockResolvedValue({ caption: "NEW IG CAPTION", iteration_id: 99 });
    renderSheet();

    await screen.findByText("Rain on the north pasture");
    const callsBefore = mockGetIterations.mock.calls.length;

    await user.type(
      screen.getByRole("textbox", { name: "Refine Instagram caption" }),
      "warmer",
    );
    await user.click(screen.getAllByRole("button", { name: /iterate/i })[0]);

    await waitFor(() => {
      expect(mockIterate).toHaveBeenCalledWith({
        content_row_id: 7,
        platform: "instagram",
        instruction: "warmer",
        mode: "refine",
      });
    });

    // Caption updated in place, history refetched
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: "Instagram caption" })).toHaveValue(
        "NEW IG CAPTION",
      );
      expect(mockGetIterations.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("shows history newest-first with the current version marked, and restores older versions", async () => {
    const user = userEvent.setup();
    mockRevertCaption.mockResolvedValue({ caption: "First pass caption", iteration_id: 13 });
    renderSheet();

    await screen.findByText("Rain on the north pasture");

    // Newest iteration is current; the older one offers Restore
    expect(screen.getByText("warmer, mention the calves")).toBeInTheDocument();
    expect(screen.getByText("current")).toBeInTheDocument();
    expect(screen.getByText("Original draft")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Restore" }));

    await waitFor(() => {
      expect(mockRevertCaption).toHaveBeenCalledWith(7, "instagram", 11);
    });
    expect(
      screen.getByText(/Every version is kept\. Restoring never deletes — it adds\./),
    ).toBeInTheDocument();
  });

  it("wires the require-review toggle to the API", async () => {
    const user = userEvent.setup();
    mockSetRequireReview.mockResolvedValue({ ...baseRow, require_review: true });
    renderSheet();

    await screen.findByText("Rain on the north pasture");

    const toggle = screen.getByRole("switch", { name: "Require review before release" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    await user.click(toggle);

    await waitFor(() => {
      expect(mockSetRequireReview).toHaveBeenCalledWith(7, true);
    });
    expect(toggle).toHaveAttribute("aria-checked", "true");
  });

  it("blocks approve while an image is missing alt text and unblocks after saving it", async () => {
    const user = userEvent.setup();
    const rowNoAlt = { ...baseRow, media_url: "https://drive.google.com/file/abc" };
    mockGetContentRow.mockResolvedValue(rowNoAlt);
    mockSetAltText.mockResolvedValue({ ...rowNoAlt, alt_text: "Tabby under the walnut tree" });
    renderSheet();

    await screen.findByText("Rain on the north pasture");

    // NO-ALT chip announced, approve blocked with explanation
    expect(screen.getByRole("status")).toHaveTextContent("NO-ALT");
    const approve = screen.getByRole("button", { name: /approve & schedule/i });
    expect(approve).toBeDisabled();
    expect(approve).toHaveAttribute("aria-describedby", "alt-blocker-note");
    expect(
      screen.getByText("Add alt text to 1 image before publishing"),
    ).toBeInTheDocument();

    // Save alt text → unblocks
    await user.type(
      screen.getByRole("textbox", { name: /add alt text/i }),
      "Tabby under the walnut tree",
    );
    await user.click(screen.getByRole("button", { name: "Save alt text" }));

    await waitFor(() => {
      expect(mockSetAltText).toHaveBeenCalledWith(7, "Tabby under the walnut tree");
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /approve & schedule/i })).toBeEnabled();
    });
  });

  it("approves the draft from the footer and closes", async () => {
    const user = userEvent.setup();
    mockApproveDraft.mockResolvedValue({ success: true, postiz_ids: ["p1"] });
    const { onClose, onSaved } = renderSheet();

    await screen.findByText("Rain on the north pasture");
    await user.click(screen.getByRole("button", { name: /approve & schedule/i }));

    await waitFor(() => {
      expect(mockApproveDraft).toHaveBeenCalledWith(7);
      expect(onSaved).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("saves the draft captions via Save draft", async () => {
    const user = userEvent.setup();
    mockEditDraft.mockResolvedValue(baseRow);
    const { onSaved } = renderSheet();

    await screen.findByText("Rain on the north pasture");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      expect(mockEditDraft).toHaveBeenCalledWith(7, {
        instagram: baseRow.captions.instagram,
        facebook: baseRow.captions.facebook,
      });
      expect(onSaved).toHaveBeenCalled();
    });
  });

  it("renders nothing when rowId is null", () => {
    renderSheet({ rowId: null });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a calm 'No captions yet' hint for suggestion drafts (raw_text only, no platforms/captions)", async () => {
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      raw_text: "Rama Navami — feast day, plan two posts.",
      platforms: {},
      captions: {},
      source: "suggestion",
      status: "draft",
    });
    mockGetIterations.mockResolvedValue([]);
    renderSheet();

    await screen.findByText("Rama Navami — feast day, plan two posts.");
    expect(screen.getByText("No captions yet")).toBeInTheDocument();
    expect(
      screen.getByText(/compose can grow captions from this idea/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open compose/i })).toHaveAttribute(
      "href",
      "/create",
    );
    // No caption cards for a captionless draft — the hint replaces them
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("blocks Approve for a captionless draft and explains why (regression: zero-platform approve)", async () => {
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      raw_text: "Rama Navami — feast day, plan two posts.",
      platforms: {},
      captions: {},
      source: "suggestion",
      status: "draft",
    });
    mockGetIterations.mockResolvedValue([]);
    renderSheet();

    await screen.findByText("Rama Navami — feast day, plan two posts.");
    const approve = screen.getByRole("button", { name: /approve & schedule/i });
    expect(approve).toBeDisabled();
    expect(approve).toHaveAttribute("aria-describedby", "no-captions-note");
    const note = screen.getByText("Add captions before approving.");
    expect(note).toHaveAttribute("id", "no-captions-note");
  });

  it("seeds the Create local draft when Open Compose is clicked (regression: blank composer)", async () => {
    const user = userEvent.setup();
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      raw_text: "Rama Navami — feast day, plan two posts.",
      date: "2026-07-16",
      content_pillar: "Spiritual",
      platforms: {},
      captions: {},
      source: "suggestion",
      status: "draft",
    });
    mockGetIterations.mockResolvedValue([]);
    localStorage.removeItem("gv-draft-create");
    renderSheet();

    await screen.findByText("Rama Navami — feast day, plan two posts.");
    await user.click(screen.getByRole("link", { name: /open compose/i }));

    const raw = localStorage.getItem("gv-draft-create");
    expect(raw).not.toBeNull();
    const seeded = JSON.parse(raw as string);
    expect(seeded).toMatchObject({
      seed: "Rama Navami — feast day, plan two posts.",
      pillar: "Spiritual",
      stage: "compose",
      scheduledDate: "2026-07-16",
    });
    // The generate flow always creates a NEW row — never write this row's id.
    expect(seeded.rowId).toBeUndefined();
    localStorage.removeItem("gv-draft-create");
  });
});

describe("ContentEditorSheet — autosave, countdown, and copy", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("flushes a pending autosave to the PREVIOUS row when switching rows (regression: cross-draft corruption)", async () => {
    const user = userEvent.setup();
    const rowB: ContentRow = {
      ...baseRow,
      row_number: 8,
      raw_text: "Evening bell\nSecond draft entirely.",
      captions: { instagram: "B insta caption", facebook: "B fb caption" },
    };
    mockGetContentRow.mockImplementation((id) =>
      Promise.resolve(id === 8 ? rowB : baseRow),
    );
    mockEditDraft.mockResolvedValue(baseRow);

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const view = render(
      <QueryClientProvider client={qc}>
        <ContentEditorSheet rowId={7} mode="refine" onClose={vi.fn()} />
      </QueryClientProvider>,
    );

    await screen.findByText("Rain on the north pasture");
    await user.type(screen.getByRole("textbox", { name: "Instagram caption" }), "!");

    // Repoint the persistent sheet to row B BEFORE the 900ms debounce fires
    view.rerender(
      <QueryClientProvider client={qc}>
        <ContentEditorSheet rowId={8} mode="refine" onClose={vi.fn()} />
      </QueryClientProvider>,
    );

    // Row A's keystrokes flushed immediately, addressed to row A with row A's captions
    expect(mockEditDraft).toHaveBeenCalledTimes(1);
    expect(mockEditDraft).toHaveBeenCalledWith(7, {
      instagram: `${baseRow.captions.instagram}!`,
      facebook: baseRow.captions.facebook,
    });

    // Row B loads; the stale timer must never fire a second (cross-row) save
    await screen.findByText("Evening bell");
    await new Promise((resolve) => setTimeout(resolve, 1100));
    expect(mockEditDraft).toHaveBeenCalledTimes(1);
  });

  it("flushes a pending autosave when the sheet closes so last keystrokes are kept", async () => {
    const user = userEvent.setup();
    mockEditDraft.mockResolvedValue(baseRow);
    const { unmount } = renderSheet();

    await screen.findByText("Rain on the north pasture");
    await user.type(screen.getByRole("textbox", { name: "Facebook caption" }), "?");

    unmount();

    expect(mockEditDraft).toHaveBeenCalledTimes(1);
    expect(mockEditDraft).toHaveBeenCalledWith(7, {
      instagram: baseRow.captions.instagram,
      facebook: `${baseRow.captions.facebook}?`,
    });
  });

  it("ticks the release countdown while the sheet is open (regression: frozen remaining)", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-07-10T12:00:00Z"));
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      auto_publish_at: "2026-07-10T13:30:00Z",
    });
    renderSheet();

    expect(await screen.findByText("in 1h 30m")).toBeInTheDocument();

    // Two 30s ticks — the countdown re-renders with fresh Date.now()
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByText("in 1h 29m")).toBeInTheDocument();
  });

  it("says 'the other caption holds still' with two platforms", async () => {
    renderSheet();
    await screen.findByText("Rain on the north pasture");
    expect(screen.getByText(/the other caption holds still/)).toBeInTheDocument();
  });

  it("counts the other captions with five platforms", async () => {
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      platforms: {
        instagram: true,
        facebook: true,
        tiktok: true,
        threads: true,
        linkedin: true,
      },
    });
    renderSheet();
    await screen.findByText("Rain on the north pasture");
    expect(screen.getByText(/the other 4 captions hold still/)).toBeInTheDocument();
  });

  it("hides the hold-still note when only one platform is enabled", async () => {
    mockGetContentRow.mockResolvedValue({
      ...baseRow,
      platforms: { instagram: true },
      captions: { instagram: "Solo caption" },
    });
    renderSheet();
    await screen.findByText("Rain on the north pasture");
    expect(screen.queryByText(/holds? still/)).not.toBeInTheDocument();
  });
});

describe("ContentEditorSheet — repurpose mode", () => {
  it("shows the source post, seeded carry-forward chips, and the explainer", async () => {
    const user = userEvent.setup();
    renderSheet({ mode: "repurpose" });

    await screen.findAllByText("Rain on the north pasture");
    expect(screen.getByText("Repurpose")).toBeInTheDocument();
    expect(screen.getByText("The source")).toBeInTheDocument();
    expect(screen.getByText("Carry forward")).toBeInTheDocument();

    // Seeded chips: pillar, first hashtags, platform set
    expect(screen.getByText("Cow Life")).toBeInTheDocument();
    expect(screen.getByText("#farmlife")).toBeInTheDocument();
    // Appears as both the source subtitle and a carry-forward chip
    expect(screen.getAllByText("Instagram + Facebook").length).toBeGreaterThanOrEqual(2);

    expect(
      screen.getByText(/Claude drafts fresh captions from this post's DNA\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Creates a new draft — the original post is untouched."),
    ).toBeInTheDocument();

    // Chips are removable
    const removeButtons = screen.getAllByRole("button", { name: "Remove" });
    await user.click(removeButtons[0]);
    expect(screen.queryByText("Cow Life")).not.toBeInTheDocument();
  });

  it("generates a NEW draft and never edits the original row", async () => {
    const user = userEvent.setup();
    mockRequest.mockResolvedValue({ captions: {}, row_id: 42 });
    const { onClose, onSaved } = renderSheet({ mode: "repurpose" });

    await screen.findAllByText("Rain on the north pasture");

    await user.type(
      screen.getByRole("textbox", { name: "New direction" }),
      "Evening bell this time",
    );
    await user.click(screen.getByRole("button", { name: /generate captions/i }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledTimes(1);
    });
    const [path, options] = mockRequest.mock.calls[0];
    expect(path).toBe("/api/generate-sync?persist=true");
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.platforms).toEqual(["instagram", "facebook"]);
    expect(body.raw_text).toContain("Rain on the north pasture");
    expect(body.raw_text).toContain("New direction: Evening bell this time");
    expect(body.raw_text).toContain("Carry forward:");

    // The original post is untouched
    expect(mockEditDraft).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("cancel closes without generating", async () => {
    const user = userEvent.setup();
    const { onClose } = renderSheet({ mode: "repurpose" });

    await screen.findAllByText("Rain on the north pasture");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalled();
    expect(mockRequest).not.toHaveBeenCalled();
  });
});
