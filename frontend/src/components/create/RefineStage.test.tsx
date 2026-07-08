import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import type { CreateDraft } from "@/hooks/useLocalDraft";
import { RefineStage } from "./RefineStage";

vi.mock("@/lib/api", () => ({
  api: {
    getIterations: vi.fn().mockResolvedValue([]),
    iterate: vi.fn(),
    revertCaption: vi.fn(),
  },
}));

vi.mock("./PreviewRail", () => ({
  PreviewRail: () => <div data-testid="preview-rail" />,
}));

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
