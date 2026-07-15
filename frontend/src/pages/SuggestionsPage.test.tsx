import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SuggestionsPage } from "./SuggestionsPage";
import type { SuggestionItem } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getSuggestions: vi.fn(),
    refreshSuggestions: vi.fn(),
    draftSuggestion: vi.fn(),
    dismissSuggestion: vi.fn(),
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

const mockGetSuggestions = vi.mocked(api.getSuggestions);
const mockRefreshSuggestions = vi.mocked(api.refreshSuggestions);
const mockDraftSuggestion = vi.mocked(api.draftSuggestion);
const mockDismissSuggestion = vi.mocked(api.dismissSuggestion);

function suggestion(overrides: Partial<SuggestionItem>): SuggestionItem {
  return {
    id: 1,
    type: "festival",
    title: "Rama Navami",
    note: "Feast day — plan a morning invite and an evening recap.",
    pillar: null,
    date: "2026-07-16",
    days_until: 2,
    status: "suggested",
    ...overrides,
  };
}

const sampleSuggestions: SuggestionItem[] = [
  suggestion({
    id: 1,
    type: "festival",
    title: "Rama Navami",
    date: "2026-07-16",
    days_until: 2,
  }),
  suggestion({
    id: 2,
    type: "pillar_gap",
    title: "Cow Life pillar is quiet",
    note: "Consider a Tabby spotlight — she turns 4 this week.",
    pillar: "Cow Life",
    date: null,
    days_until: null,
  }),
  suggestion({
    id: 3,
    type: "template",
    title: "Weekly cow spotlight — due Thursday",
    note: "Fill in this week's cow name.",
    date: "2026-07-17",
    days_until: 3,
  }),
  suggestion({
    id: 4,
    type: "seasonal",
    title: "First pasture day",
    note: "The cows go out to the new pasture. Great video moment.",
    date: "2026-07-13",
    days_until: -1,
  }),
];

function renderSuggestions() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SuggestionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The tinted card element that wraps a suggestion, found from its title. */
function cardOf(title: string | RegExp): HTMLElement {
  const heading = screen.getByRole("heading", { name: title });
  const card = heading.closest("div.rounded-2xl");
  if (!(card instanceof HTMLElement)) throw new Error("card not found");
  return card;
}

describe("SuggestionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Freeze the clock so "Mar 26"-style dates are deterministic.
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-07-14T09:00:00"));
    mockGetSuggestions.mockResolvedValue({ suggestions: sampleSuggestions });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a loading skeleton grid", () => {
    mockGetSuggestions.mockReturnValue(new Promise(() => {}));
    renderSuggestions();
    expect(
      screen.getByRole("status", { name: /loading suggestions/i }),
    ).toBeInTheDocument();
  });

  it("renders the header and one card per suggestion", async () => {
    renderSuggestions();

    expect(
      await screen.findByRole("heading", { name: "Rama Navami" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("What the season is asking for."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /cow life pillar is quiet/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /weekly cow spotlight/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /first pasture day/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /draft it/i })).toHaveLength(4);
    // Auto-refresh must NOT fire when the list has items
    expect(mockRefreshSuggestions).not.toHaveBeenCalled();
  });

  it("applies tone and icon by type: festival→terra, pillar_gap→sage, template→cream, other→sage", async () => {
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    expect(cardOf("Rama Navami").className).toContain("bg-terra-50");
    expect(cardOf(/cow life pillar is quiet/i).className).toContain(
      "bg-sage-50",
    );
    expect(cardOf(/weekly cow spotlight/i).className).toContain(
      "bg-cream-100/80",
    );
    // Unknown type falls back to sage
    expect(cardOf(/first pasture day/i).className).toContain("bg-sage-50");
  });

  it("humanizes type labels in the eyebrow (pillar_gap → pillar)", async () => {
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    expect(
      within(cardOf(/cow life pillar is quiet/i)).getByText("pillar"),
    ).toBeInTheDocument();
    expect(
      within(cardOf("Rama Navami")).getByText("festival"),
    ).toBeInTheDocument();
    expect(
      within(cardOf(/first pasture day/i)).getByText("seasonal"),
    ).toBeInTheDocument();
  });

  it("formats the date as 'Jul 16' and shows 'in 2d' only for non-negative days_until", async () => {
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    const festival = cardOf("Rama Navami");
    expect(within(festival).getByText("· Jul 16")).toBeInTheDocument();
    expect(within(festival).getByText("in 2d")).toBeInTheDocument();

    // Past date (days_until = -1): date shows, countdown does not
    const seasonal = cardOf(/first pasture day/i);
    expect(within(seasonal).getByText("· Jul 13")).toBeInTheDocument();
    expect(within(seasonal).queryByText(/in -?\d+d/)).not.toBeInTheDocument();

    // Undated suggestion has neither
    const gap = cardOf(/cow life pillar is quiet/i);
    expect(within(gap).queryByText(/·/)).not.toBeInTheDocument();
  });

  it("drafts a suggestion: removes the card, toasts, and opens the editor sheet in refine mode", async () => {
    const user = userEvent.setup();
    mockDraftSuggestion.mockResolvedValue({
      id: 1,
      status: "drafted",
      content_row_id: 42,
    });
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    await user.click(
      within(cardOf("Rama Navami")).getByRole("button", { name: /draft it/i }),
    );

    await waitFor(() => {
      expect(mockDraftSuggestion).toHaveBeenCalledWith(1);
    });
    expect(screen.getByTestId("editor-sheet")).toHaveTextContent(
      "Editing row 42 in refine mode",
    );
    expect(
      screen.queryByRole("heading", { name: "Rama Navami" }),
    ).not.toBeInTheDocument();
    expect(toast.success).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /close editor/i }));
    expect(screen.queryByTestId("editor-sheet")).not.toBeInTheDocument();
  });

  it("disables the Draft it button while drafting (double-click guard)", async () => {
    const user = userEvent.setup();
    let resolveDraft!: (v: {
      id: number;
      status: string;
      content_row_id: number;
    }) => void;
    mockDraftSuggestion.mockReturnValue(
      new Promise((resolve) => {
        resolveDraft = resolve;
      }),
    );
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    const button = within(cardOf("Rama Navami")).getByRole("button", {
      name: /draft it/i,
    });
    await user.click(button);
    expect(
      within(cardOf("Rama Navami")).getByRole("button", { name: /drafting/i }),
    ).toBeDisabled();
    await user.click(
      within(cardOf("Rama Navami")).getByRole("button", { name: /drafting/i }),
    );

    resolveDraft({ id: 1, status: "drafted", content_row_id: 42 });
    await waitFor(() => {
      expect(screen.getByTestId("editor-sheet")).toBeInTheDocument();
    });
    expect(mockDraftSuggestion).toHaveBeenCalledTimes(1);
  });

  it("dismisses a suggestion optimistically and restores it on failure", async () => {
    const user = userEvent.setup();
    let rejectDismiss!: (err: Error) => void;
    mockDismissSuggestion.mockReturnValue(
      new Promise((_resolve, reject) => {
        rejectDismiss = reject;
      }),
    );
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    await user.click(
      within(cardOf("Rama Navami")).getByRole("button", { name: /dismiss/i }),
    );

    // Optimistic removal — card gone before the API answers
    expect(
      screen.queryByRole("heading", { name: "Rama Navami" }),
    ).not.toBeInTheDocument();
    expect(mockDismissSuggestion).toHaveBeenCalledWith(1);

    rejectDismiss(new Error("boom"));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Rama Navami" }),
      ).toBeInTheDocument();
    });
    expect(toast.error).toHaveBeenCalled();
  });

  it("dismisses for good on success and toasts without undo", async () => {
    const user = userEvent.setup();
    mockDismissSuggestion.mockResolvedValue({ id: 2, status: "dismissed" });
    renderSuggestions();
    await screen.findByRole("heading", { name: /cow life pillar is quiet/i });

    await user.click(
      within(cardOf(/cow life pillar is quiet/i)).getByRole("button", {
        name: /dismiss/i,
      }),
    );

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
    expect(
      screen.queryByRole("heading", { name: /cow life pillar is quiet/i }),
    ).not.toBeInTheDocument();
  });

  it("auto-fires refreshSuggestions ONCE when the first fetch is empty", async () => {
    mockGetSuggestions.mockResolvedValue({ suggestions: [] });
    mockRefreshSuggestions.mockResolvedValue({
      suggestions: [sampleSuggestions[0]],
    });
    renderSuggestions();

    await waitFor(() => {
      expect(mockRefreshSuggestions).toHaveBeenCalledTimes(1);
    });
    // Seeded cards land on the page
    expect(
      await screen.findByRole("heading", { name: "Rama Navami" }),
    ).toBeInTheDocument();
    expect(mockRefreshSuggestions).toHaveBeenCalledTimes(1);
  });

  it("shows the calm empty state with a Refresh action when a refresh returns nothing", async () => {
    const user = userEvent.setup();
    mockGetSuggestions.mockResolvedValue({ suggestions: [] });
    mockRefreshSuggestions.mockResolvedValue({ suggestions: [] });
    renderSuggestions();

    await waitFor(() => {
      expect(screen.getByText("The season is quiet.")).toBeInTheDocument();
    });
    expect(screen.getByText(/refresh to ask again/i)).toBeInTheDocument();

    // The empty-state Refresh action fires the mutation again
    const buttons = screen.getAllByRole("button", { name: /^refresh$/i });
    await user.click(buttons[buttons.length - 1]);
    await waitFor(() => {
      // once from self-seed + once from the click
      expect(mockRefreshSuggestions).toHaveBeenCalledTimes(2);
    });
  });

  it("refreshes from the header button and replaces the list", async () => {
    const user = userEvent.setup();
    mockRefreshSuggestions.mockResolvedValue({
      suggestions: [
        suggestion({ id: 9, type: "festival", title: "Hanuman Jayanti" }),
      ],
    });
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    await user.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => {
      expect(mockRefreshSuggestions).toHaveBeenCalledTimes(1);
    });
    expect(
      await screen.findByRole("heading", { name: "Hanuman Jayanti" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Rama Navami" }),
    ).not.toBeInTheDocument();
  });

  it("disables each card's Draft/Dismiss while a refresh is in flight (regression: dismissed card resurrection)", async () => {
    const user = userEvent.setup();
    let resolveRefresh!: (v: { suggestions: SuggestionItem[] }) => void;
    mockRefreshSuggestions.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve;
      }),
    );
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    await user.click(screen.getByRole("button", { name: /refresh/i }));

    // Every card's actions are locked while the new list is in flight
    const card = cardOf("Rama Navami");
    expect(within(card).getByRole("button", { name: /draft it/i })).toBeDisabled();
    expect(within(card).getByRole("button", { name: /dismiss/i })).toBeDisabled();

    resolveRefresh({ suggestions: sampleSuggestions });
    await waitFor(() => {
      expect(
        within(cardOf("Rama Navami")).getByRole("button", { name: /draft it/i }),
      ).toBeEnabled();
    });
    expect(
      within(cardOf("Rama Navami")).getByRole("button", { name: /dismiss/i }),
    ).toBeEnabled();
  });

  it("does not resurrect a suggestion dismissed while a refresh response lands", async () => {
    const user = userEvent.setup();
    mockDismissSuggestion.mockResolvedValue({ id: 1, status: "dismissed" });
    let resolveRefresh!: (v: { suggestions: SuggestionItem[] }) => void;
    mockRefreshSuggestions.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve;
      }),
    );
    renderSuggestions();
    await screen.findByRole("heading", { name: "Rama Navami" });

    // Dismiss first, then refresh — the stale response still includes id 1
    await user.click(
      within(cardOf("Rama Navami")).getByRole("button", { name: /dismiss/i }),
    );
    await waitFor(() => {
      expect(mockDismissSuggestion).toHaveBeenCalledWith(1);
    });
    await user.click(screen.getByRole("button", { name: /refresh/i }));
    resolveRefresh({ suggestions: sampleSuggestions });

    await waitFor(() => {
      expect(mockRefreshSuggestions).toHaveBeenCalledTimes(1);
    });
    // The dismissed card stays gone; the rest of the list lands normally
    expect(
      screen.queryByRole("heading", { name: "Rama Navami" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /weekly cow spotlight/i }),
    ).toBeInTheDocument();
  });

  it("degrades quietly when the suggestions query fails", async () => {
    mockGetSuggestions.mockRejectedValue(new Error("down"));
    renderSuggestions();

    await waitFor(() => {
      expect(screen.getByText("Suggestions are resting.")).toBeInTheDocument();
    });
    // Header + empty-state action both offer a way back
    expect(
      screen.getAllByRole("button", { name: /refresh/i }).length,
    ).toBeGreaterThanOrEqual(1);
  });
});
