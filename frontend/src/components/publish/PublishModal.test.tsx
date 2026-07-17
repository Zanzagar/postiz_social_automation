import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PublishNowResponse } from "@/lib/api";
import { PublishModal } from "./PublishModal";

vi.mock("@/lib/api", () => ({
  api: {
    publishNow: vi.fn(),
  },
  ApiError: class extends Error {
    status: number;
    detail: string;
    constructor(s: number, d: string) {
      super(d);
      this.name = "ApiError";
      this.status = s;
      this.detail = d;
    }
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}));

import { api, ApiError } from "@/lib/api";
import { toast } from "sonner";

const mockPublishNow = vi.mocked(api.publishNow);

function response(overrides: Partial<PublishNowResponse> = {}): PublishNowResponse {
  return {
    row_id: 12,
    results: [
      {
        platform: "instagram",
        status: "posted",
        postiz_id: "pz-1",
        error: null,
        link: "https://instagram.com/p/abc",
      },
      {
        platform: "facebook",
        status: "posted",
        postiz_id: "pz-2",
        error: null,
        link: null,
      },
    ],
    status: "posted",
    posted_at: "2026-07-16T11:04:00",
    ...overrides,
  };
}

function renderModal(props: Partial<Parameters<typeof PublishModal>[0]> = {}) {
  const onClose = vi.fn();
  const onDone = vi.fn();
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <PublishModal
      rowId={12}
      platforms={["instagram", "facebook"]}
      title="Rama Navami — feast tomorrow"
      captions={{
        instagram:
          "The feast is tomorrow — Lakshmi and her calf lead the procession through the lower pasture at dawn.",
        facebook: "FB caption",
      }}
        onClose={onClose}
        onDone={onDone}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { onClose, onDone };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PublishModal pending state", () => {
  it("calls publishNow on mount exactly once and shows Sending rows", async () => {
    mockPublishNow.mockReturnValue(new Promise(() => {}));
    renderModal();

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await waitFor(() => expect(mockPublishNow).toHaveBeenCalledWith(12));
    expect(mockPublishNow).toHaveBeenCalledTimes(1);

    expect(screen.getAllByText("Sending…")).toHaveLength(2);
    expect(screen.getByText("Instagram")).toBeInTheDocument();
    expect(screen.getByText("Facebook")).toBeInTheDocument();
    expect(
      screen.getByText("0 of 2 platforms published"),
    ).toBeInTheDocument();
  });
});

describe("PublishModal success", () => {
  it("renders posted rows with time, link buttons, footer count, and fires toasts", async () => {
    mockPublishNow.mockResolvedValue(response());
    const { onDone } = renderModal();

    expect(await screen.findAllByText("Posted · 11:04 AM")).toHaveLength(2);
    expect(
      screen.getByText("2 of 2 platforms published"),
    ).toBeInTheDocument();

    // Link only for the platform that returned one
    const view = screen.getByRole("link", { name: "View on Instagram" });
    expect(view).toHaveAttribute("href", "https://instagram.com/p/abc");
    expect(
      screen.queryByRole("link", { name: "View on Facebook" }),
    ).not.toBeInTheDocument();

    expect(toast.success).toHaveBeenCalledTimes(2);
    expect(toast.success).toHaveBeenCalledWith(
      "Posted to Instagram",
      expect.objectContaining({
        description: expect.stringMatching(/^The feast is tomorrow/),
        action: expect.objectContaining({ label: "View" }),
      }),
    );
    // No link → no View action
    expect(toast.success).toHaveBeenCalledWith(
      "Posted to Facebook",
      expect.objectContaining({ action: undefined }),
    );
    expect(toast.warning).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledWith(response());
  });

  it("truncates the toast description to ~60 chars of the real caption", async () => {
    mockPublishNow.mockResolvedValue(response());
    renderModal();
    await screen.findAllByText("Posted · 11:04 AM");

    const call = vi
      .mocked(toast.success)
      .mock.calls.find(([msg]) => msg === "Posted to Instagram");
    const description = (call?.[1] as { description?: string }).description ?? "";
    expect(description.length).toBeLessThanOrEqual(61); // 60 + ellipsis
    expect(description.endsWith("…")).toBe(true);
  });
});

describe("PublishModal scheduled", () => {
  it("renders scheduled rows with the scheduled date", async () => {
    mockPublishNow.mockResolvedValue(
      response({
        results: [
          {
            platform: "instagram",
            status: "scheduled",
            postiz_id: "pz-9",
            error: null,
            link: null,
          },
        ],
        status: "approved",
        posted_at: null,
      }),
    );
    renderModal({ platforms: ["instagram"], scheduledFor: "2026-07-18" });

    expect(await screen.findByText("Scheduled · Jul 18")).toBeInTheDocument();
    expect(
      screen.getByText("0 of 1 platforms published"),
    ).toBeInTheDocument();
    expect(toast.success).not.toHaveBeenCalled();
  });
});

describe("PublishModal partial failure", () => {
  it("shows the real error text, marks it as an alert, and warns via toast", async () => {
    mockPublishNow.mockResolvedValue(
      response({
        results: [
          response().results[0],
          {
            platform: "tiktok",
            status: "failed",
            postiz_id: null,
            error:
              "Media isn't publicly reachable — import it to Google Drive first, then reattach",
            link: null,
          },
        ],
      }),
    );
    renderModal({ platforms: ["instagram", "tiktok"] });

    const error = await screen.findByText(/Media isn't publicly reachable/);
    expect(error).toHaveAttribute(
      "title",
      "Media isn't publicly reachable — import it to Google Drive first, then reattach",
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText("1 of 2 platforms published"),
    ).toBeInTheDocument();
    expect(toast.warning).toHaveBeenCalledWith(
      "Published to 1 of 2 — TikTok failed",
    );
    // Success toast still fires for the platform that went out
    expect(toast.success).toHaveBeenCalledTimes(1);
  });
});

describe("PublishModal request-level failure", () => {
  it("surfaces the ApiError detail (429 budget) as an alert", async () => {
    mockPublishNow.mockRejectedValue(
      new ApiError(
        429,
        "Postiz hourly request budget exhausted — try again in a few minutes",
      ),
    );
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/budget exhausted/);
    expect(
      screen.getByText("0 of 2 platforms published"),
    ).toBeInTheDocument();
  });

  it("maps alt_text_required to friendly copy with the raw detail as title", async () => {
    mockPublishNow.mockRejectedValue(new ApiError(422, "alt_text_required"));
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Add alt text to the image before publishing.",
    );
    expect(alert).toHaveAttribute("title", "alt_text_required");
  });

  it("maps a 502 to the Postiz connection message, keeping internals in title", async () => {
    mockPublishNow.mockRejectedValue(
      new ApiError(502, "HTTPError 502 at http://sethpc.xyz:5000/api/public/v1/posts"),
    );
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Couldn't reach Postiz — check the connection on the Health page.",
    );
    expect(alert).toHaveAttribute(
      "title",
      "HTTPError 502 at http://sethpc.xyz:5000/api/public/v1/posts",
    );
  });

  it("maps details starting with 'Postiz error' to the connection message", async () => {
    mockPublishNow.mockRejectedValue(new ApiError(500, "Postiz error: 401"));
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Couldn't reach Postiz — check the connection on the Health page.",
    );
    expect(alert).toHaveAttribute("title", "Postiz error: 401");
  });

  it("maps anything else to a generic retry message with the raw detail as title", async () => {
    mockPublishNow.mockRejectedValue(
      new ApiError(500, "IntegrityError: UNIQUE constraint failed content.id"),
    );
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Publishing failed — try again.");
    expect(alert).toHaveAttribute(
      "title",
      "IntegrityError: UNIQUE constraint failed content.id",
    );
  });

  it("maps non-Api errors (network) to the generic retry message", async () => {
    mockPublishNow.mockRejectedValue(new TypeError("Failed to fetch"));
    renderModal();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Publishing failed — try again.");
    expect(alert).toHaveAttribute("title", "Failed to fetch");
  });
});

describe("PublishModal already-published rows", () => {
  it("renders 'Posted earlier' without a success toast for the flagged row in a mixed response", async () => {
    mockPublishNow.mockResolvedValue(
      response({
        results: [
          {
            platform: "instagram",
            status: "posted",
            postiz_id: "pz-1",
            error: null,
            link: null,
          },
          {
            platform: "facebook",
            status: "posted",
            postiz_id: "pz-0",
            error: null,
            link: null,
            already_published: true,
          },
        ],
      }),
    );
    renderModal();

    expect(await screen.findByText("Posted earlier")).toBeInTheDocument();
    // Freshly posted row keeps its time; earlier row shows no time
    expect(screen.getByText("Posted · 11:04 AM")).toBeInTheDocument();
    // Footer counts the earlier row as published
    expect(screen.getByText("2 of 2 platforms published")).toBeInTheDocument();
    // Only the freshly posted platform toasts
    expect(toast.success).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalledWith(
      "Posted to Instagram",
      expect.anything(),
    );
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("shows all rows, a full footer count, and zero toasts when everything was already published", async () => {
    mockPublishNow.mockResolvedValue(
      response({
        results: [
          {
            platform: "instagram",
            status: "posted",
            postiz_id: "pz-1",
            error: null,
            link: null,
            already_published: true,
          },
          {
            platform: "facebook",
            status: "posted",
            postiz_id: "pz-2",
            error: null,
            link: null,
            already_published: true,
          },
        ],
      }),
    );
    renderModal();

    expect(await screen.findAllByText("Posted earlier")).toHaveLength(2);
    expect(screen.getByText("Instagram")).toBeInTheDocument();
    expect(screen.getByText("Facebook")).toBeInTheDocument();
    expect(screen.getByText("2 of 2 platforms published")).toBeInTheDocument();
    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.warning).not.toHaveBeenCalled();
  });
});

describe("PublishModal close", () => {
  it("fires onClose from the footer Close button", async () => {
    const user = userEvent.setup();
    mockPublishNow.mockResolvedValue(response());
    const { onClose } = renderModal();
    await screen.findAllByText("Posted · 11:04 AM");

    // Both the GVSheet header X and the footer ghost button are named
    // "Close" — the footer one renders last.
    const closeButtons = screen.getAllByRole("button", { name: "Close" });
    await user.click(closeButtons[closeButtons.length - 1]);
    expect(onClose).toHaveBeenCalled();
  });
});
