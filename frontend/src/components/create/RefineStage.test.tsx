import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CreateDraft } from "@/hooks/useLocalDraft";
import { api } from "@/lib/api";
import { RefineStage } from "./RefineStage";

vi.mock("@/lib/api", () => ({
  api: {
    getIterations: vi.fn(),
    getHashtagSuggestions: vi.fn(),
    iterate: vi.fn(),
    revertCaption: vi.fn(),
  },
}));

vi.mock("./PreviewRail", () => ({
  PreviewRail: () => <div data-testid="preview-rail" />,
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
