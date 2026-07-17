import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CreateDraft } from "@/hooks/useLocalDraft";
import { api, type ContentRow } from "@/lib/api";
import { RefineStage } from "./RefineStage";

vi.mock("@/lib/api", () => ({
  api: {
    getIterations: vi.fn(),
    getHashtagSuggestions: vi.fn(),
    iterate: vi.fn(),
    revertCaption: vi.fn(),
    editDraft: vi.fn(),
    setAltText: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { toast } from "sonner";

vi.mock("./PreviewRail", () => ({
  PreviewRail: () => <div data-testid="preview-rail" />,
}));

vi.mock("@/components/publish/PublishModal", () => ({
  PublishModal: ({
    rowId,
    platforms,
    onClose,
  }: {
    rowId: number;
    platforms: string[];
    onClose: () => void;
  }) => (
    <div data-testid="publish-modal">
      Publishing row {rowId} to {platforms.join(",")}
      <button onClick={onClose}>Close publish modal</button>
    </div>
  ),
}));

const SUGGESTIONS = {
  hashtags: [
    { hashtag: "gitavalley", avg_engagement: 12.4, times_used: 9, trend: "rising" },
    { hashtag: "farmlife", avg_engagement: 8.1, times_used: 4, trend: "stable" },
    { hashtag: "krishna", avg_engagement: 5.2, times_used: 2, trend: "stable" },
  ],
  source: "performance",
};

function seedMocks() {
  vi.mocked(api.getIterations).mockResolvedValue([]);
  vi.mocked(api.getHashtagSuggestions).mockResolvedValue(SUGGESTIONS);
  vi.mocked(api.editDraft).mockResolvedValue({} as ContentRow);
  vi.mocked(api.setAltText).mockResolvedValue({} as ContentRow);
}

beforeEach(() => {
  vi.clearAllMocks();
  seedMocks();
});

function draft(overrides: Partial<CreateDraft> = {}): CreateDraft {
  return {
    seed: "Calves in the pasture",
    platforms: ["instagram", "facebook", "youtube"],
    pillar: "Cow Life",
    scheduledDate: "2026-07-08",
    scheduledTime: "09:00",
    mediaUrl: "",
    altText: "",
    stage: "refine",
    rowId: 12,
    captions: { instagram: "IG caption", facebook: "FB caption", youtube: "YT caption" },
    ...overrides,
  };
}

function renderStage(d: CreateDraft = draft()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const update = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <RefineStage
        draft={d}
        update={update}
        onSaveDraft={() => {}}
        onSend={() => {}}
        isSaving={false}
        isSending={false}
      />
    </QueryClientProvider>,
  );
  return { update };
}

describe("RefineStage platform tabs (roving tabindex)", () => {
  it("gives the active tab tabIndex 0 and all others -1", () => {
    renderStage();
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[0]).toHaveAttribute("tabindex", "0");
    expect(tabs[1]).toHaveAttribute("tabindex", "-1");
    expect(tabs[2]).toHaveAttribute("tabindex", "-1");
  });

  it("ArrowRight moves focus to and selects the next tab", async () => {
    const user = userEvent.setup();
    renderStage();
    const tabs = screen.getAllByRole("tab");
    tabs[0].focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getAllByRole("tab")[1]).toHaveFocus();
    expect(screen.getAllByRole("tab")[1]).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tab")[1]).toHaveAttribute("tabindex", "0");
    expect(screen.getAllByRole("tab")[0]).toHaveAttribute("tabindex", "-1");
  });

  it("ArrowLeft wraps from the first tab to the last", async () => {
    const user = userEvent.setup();
    renderStage();
    screen.getAllByRole("tab")[0].focus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getAllByRole("tab")[2]).toHaveFocus();
    expect(screen.getAllByRole("tab")[2]).toHaveAttribute("aria-selected", "true");
  });

  it("Home and End jump to the first and last tabs", async () => {
    const user = userEvent.setup();
    renderStage();
    screen.getAllByRole("tab")[0].focus();
    await user.keyboard("{End}");
    expect(screen.getAllByRole("tab")[2]).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getAllByRole("tab")[0]).toHaveFocus();
    expect(screen.getAllByRole("tab")[0]).toHaveAttribute("aria-selected", "true");
  });
});

describe("RefineStage NO ALT chip", () => {
  it("announces the missing-alt warning via role=status", () => {
    renderStage(draft({ mediaUrl: "https://example.com/cow.jpg", altText: "" }));
    expect(screen.getByRole("status")).toHaveTextContent("NO ALT");
  });

  it("does not render the chip when alt text is present", () => {
    renderStage(draft({ mediaUrl: "https://example.com/cow.jpg", altText: "A cow" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("RefineStage suggested hashtags", () => {
  it("renders suggestion chips minus tags already in the active caption (case-insensitive)", async () => {
    renderStage(
      draft({
        captions: {
          instagram: "IG caption #FarmLife",
          facebook: "FB caption",
          youtube: "YT caption",
        },
      }),
    );

    expect(await screen.findByRole("button", { name: "#gitavalley" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "#krishna" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "#farmlife" })).not.toBeInTheDocument();
    expect(screen.getByText("Suggested tags")).toBeInTheDocument();
    expect(screen.getByText("From your post history")).toBeInTheDocument();
    expect(api.getHashtagSuggestions).toHaveBeenCalledWith("instagram", 8);
  });

  it("shows a trend hint via the title attribute", async () => {
    renderStage();
    const chip = await screen.findByRole("button", { name: "#gitavalley" });
    expect(chip).toHaveAttribute("title", "used 9 times");
  });

  it("appends the tag to the active caption through the change handler on click", async () => {
    const user = userEvent.setup();
    const { update } = renderStage();

    await user.click(await screen.findByRole("button", { name: "#gitavalley" }));

    expect(update).toHaveBeenCalledWith({
      captions: {
        instagram: "IG caption #gitavalley",
        facebook: "FB caption",
        youtube: "YT caption",
      },
    });
  });

  it("is hidden entirely for Threads (hashMax 0)", async () => {
    renderStage(
      draft({ platforms: ["threads"], captions: { threads: "Quiet morning at the barn" } }),
    );

    await waitFor(() => expect(api.getIterations).toHaveBeenCalled());
    expect(screen.queryByText("Suggested tags")).not.toBeInTheDocument();
    expect(api.getHashtagSuggestions).not.toHaveBeenCalled();
  });

  it("disables chips at the platform hashtag max and never exceeds it", async () => {
    const user = userEvent.setup();
    const { update } = renderStage(
      draft({
        platforms: ["facebook"],
        captions: { facebook: "FB caption #a #b #c #d #e" },
      }),
    );

    const chip = await screen.findByRole("button", { name: "#gitavalley" });
    expect(chip).toHaveAttribute("aria-disabled", "true");
    await user.click(chip);
    expect(update).not.toHaveBeenCalled();
  });

  it("renders nothing when the suggestion fetch fails (quiet degrade)", async () => {
    vi.mocked(api.getHashtagSuggestions).mockRejectedValue(new Error("boom"));
    renderStage();

    await waitFor(() => expect(api.getHashtagSuggestions).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByText("Suggested tags")).not.toBeInTheDocument(),
    );
  });

  it("renders nothing when the suggestion list is empty", async () => {
    vi.mocked(api.getHashtagSuggestions).mockResolvedValue({
      hashtags: [],
      source: "performance",
    });
    renderStage();

    await waitFor(() => expect(api.getHashtagSuggestions).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByText("Suggested tags")).not.toBeInTheDocument(),
    );
  });

  it("shows the label with skeleton chips while loading", async () => {
    vi.mocked(api.getHashtagSuggestions).mockImplementation(
      () => new Promise(() => undefined),
    );
    renderStage();

    expect(await screen.findByText("Suggested tags")).toBeInTheDocument();
    expect(screen.queryByText("From your post history")).not.toBeInTheDocument();
  });
});

describe("RefineStage publish now", () => {
  it("renders a primary Publish now button beside a secondary Send to Postiz", () => {
    renderStage();
    const publish = screen.getByRole("button", { name: /publish now/i });
    const send = screen.getByRole("button", { name: /send to postiz/i });
    expect(publish).toBeInTheDocument();
    expect(send).toBeInTheDocument();
    expect(publish).toHaveAttribute("data-variant", "default");
    expect(send).toHaveAttribute("data-variant", "secondary");
  });

  it("opens the PublishModal for the current row and enabled platforms", async () => {
    const user = userEvent.setup();
    renderStage();

    await user.click(screen.getByRole("button", { name: /publish now/i }));

    expect(screen.getByTestId("publish-modal")).toHaveTextContent(
      "Publishing row 12 to instagram,facebook,youtube",
    );

    await user.click(
      screen.getByRole("button", { name: /close publish modal/i }),
    );
    expect(screen.queryByTestId("publish-modal")).not.toBeInTheDocument();
  });

  it("is disabled when alt text is missing", () => {
    renderStage(draft({ mediaUrl: "https://example.com/cow.jpg", altText: "" }));
    expect(screen.getByRole("button", { name: /publish now/i })).toBeDisabled();
  });

  it("is disabled when the draft has no saved row", () => {
    renderStage(draft({ rowId: null }));
    expect(screen.getByRole("button", { name: /publish now/i })).toBeDisabled();
  });

  it("explains the no-row disabled state via aria-describedby (Save to drafts first)", () => {
    renderStage(draft({ rowId: null }));
    const publish = screen.getByRole("button", { name: /publish now/i });
    expect(publish).toBeDisabled();
    const describedBy = publish.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const hint = describedBy!
      .split(" ")
      .map((id) => document.getElementById(id)?.textContent ?? "")
      .join(" ");
    expect(hint).toMatch(/save to drafts first/i);
  });
});

describe("RefineStage publish now persists local edits first", () => {
  it("persists edited captions, the platform dict, and alt text before opening the modal", async () => {
    const user = userEvent.setup();
    renderStage(
      draft({ mediaUrl: "https://example.com/cow.jpg", altText: "A cow at dawn" }),
    );

    await user.click(screen.getByRole("button", { name: /publish now/i }));

    expect(api.editDraft).toHaveBeenCalledWith(
      12,
      { instagram: "IG caption", facebook: "FB caption", youtube: "YT caption" },
      { instagram: true, facebook: true, youtube: true },
    );
    expect(api.setAltText).toHaveBeenCalledWith(12, "A cow at dawn");
    expect(screen.getByTestId("publish-modal")).toHaveTextContent(
      "Publishing row 12 to instagram,facebook,youtube",
    );
  });

  it("skips setAltText when the draft has no alt text", async () => {
    const user = userEvent.setup();
    renderStage();

    await user.click(screen.getByRole("button", { name: /publish now/i }));

    expect(api.editDraft).toHaveBeenCalledTimes(1);
    expect(api.setAltText).not.toHaveBeenCalled();
    expect(screen.getByTestId("publish-modal")).toBeInTheDocument();
  });

  it("shows an aria-busy Saving… state and keeps the modal closed while persisting", async () => {
    const user = userEvent.setup();
    vi.mocked(api.editDraft).mockImplementation(
      () => new Promise<never>(() => undefined),
    );
    renderStage();

    await user.click(screen.getByRole("button", { name: /publish now/i }));

    const saving = screen.getByRole("button", { name: /saving…/i });
    expect(saving).toHaveAttribute("aria-busy", "true");
    expect(saving).toBeDisabled();
    expect(screen.queryByTestId("publish-modal")).not.toBeInTheDocument();
  });

  it("toasts and does NOT open the modal when persisting fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.editDraft).mockRejectedValue(new Error("Save failed"));
    renderStage();

    await user.click(screen.getByRole("button", { name: /publish now/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(screen.queryByTestId("publish-modal")).not.toBeInTheDocument();
    // Button recovers so the farmer can retry
    expect(
      screen.getByRole("button", { name: /publish now/i }),
    ).toBeEnabled();
  });
});
