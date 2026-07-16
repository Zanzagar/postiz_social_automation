import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarPlanDialog } from "./CalendarPlanDialog";
import type { CalendarPlanResponse } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    createCalendarPlan: vi.fn(),
    approveCalendarPlan: vi.fn(),
    deleteCalendarPlan: vi.fn(),
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

import { api, ApiError } from "@/lib/api";
import { toast } from "sonner";

const samplePlan: CalendarPlanResponse = {
  id: 5,
  date_range_start: "2026-07-06",
  date_range_end: "2026-07-12",
  platforms: ["instagram", "facebook"],
  slots: [
    {
      date: "2026-07-07",
      time: "09:00",
      pillar: "Cow Life",
      topic: "morning pasture",
      content_idea: "Tabby greets the sunrise over the east pasture",
      recommended_media_id: null,
      target_platforms: ["instagram"],
    },
  ],
  status: "draft",
  created_at: "2026-07-06T08:00:00Z",
};

function renderDialog(onOpenChange = vi.fn()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <CalendarPlanDialog
        open
        onOpenChange={onOpenChange}
        defaultStart="2026-07-06"
        defaultEnd="2026-07-12"
      />
    </QueryClientProvider>,
  );
  return onOpenChange;
}

/** Generate a plan to land in the review step. */
async function goToReview(user: ReturnType<typeof userEvent.setup>) {
  vi.mocked(api.createCalendarPlan).mockResolvedValue(samplePlan);
  await user.click(screen.getByRole("button", { name: /generate plan/i }));
  await waitFor(() => {
    expect(screen.getByText(/review plan/i)).toBeInTheDocument();
  });
}

describe("CalendarPlanDialog — discard plan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("deletes the draft plan, closes, and toasts on Discard plan", async () => {
    const user = userEvent.setup();
    vi.mocked(api.deleteCalendarPlan).mockResolvedValue({
      deleted: true,
      id: 5,
    });
    const onOpenChange = renderDialog();

    await goToReview(user);
    await user.click(screen.getByRole("button", { name: /discard plan/i }));

    await waitFor(() => {
      expect(api.deleteCalendarPlan).toHaveBeenCalledWith(5);
      expect(toast.success).toHaveBeenCalledWith("Plan discarded");
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("toasts the API detail on a 400 (non-draft) and stays open", async () => {
    const user = userEvent.setup();
    vi.mocked(api.deleteCalendarPlan).mockRejectedValue(
      new ApiError(400, "Only draft plans can be deleted"),
    );
    const onOpenChange = renderDialog();

    await goToReview(user);
    await user.click(screen.getByRole("button", { name: /discard plan/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        "Only draft plans can be deleted",
      );
    });
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByText(/review plan/i)).toBeInTheDocument();
  });
});
