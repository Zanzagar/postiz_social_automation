import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { NAV_ITEMS } from "./nav-items";
import { AuthContext, type AuthContextValue } from "@/contexts/AuthContext";
import type { ContentRow, HealthResponse } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getDrafts: vi.fn(),
    getHealth: vi.fn(),
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
const mockGetHealth = vi.mocked(api.getHealth);

const mockAuth: AuthContextValue = {
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
};

function draft(id: number, status: string): ContentRow {
  return {
    row_number: id,
    date: "2026-07-06",
    content_pillar: "Farm & Community",
    raw_text: `Tabby and Dennis grazing at sunrise (${id})`,
    media_url: null,
    platforms: { instagram: true },
    status,
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
  };
}

const healthyResponse: HealthResponse = {
  services: [
    { name: "postiz", status: "ok", message: "", last_checked: "2026-07-06T09:00:00Z" },
  ],
  errors: [],
};

function renderShell(route = "/", auth: Partial<AuthContextValue> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={[route]}>
      <QueryClientProvider client={queryClient}>
        <AuthContext.Provider value={{ ...mockAuth, ...auth }}>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<div>HOME MARKER</div>} />
              <Route path="drafts" element={<div>DRAFTS MARKER</div>} />
              <Route path="templates" element={<div>TEMPLATES MARKER</div>} />
              <Route path="create" element={<div>CREATE MARKER</div>} />
            </Route>
          </Routes>
        </AuthContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetDrafts.mockResolvedValue([]);
  mockGetHealth.mockResolvedValue(healthyResponse);
});

describe("AppShell layout", () => {
  it("renders branding and tagline", () => {
    renderShell();
    expect(screen.getByText("Gita Valley")).toBeInTheDocument();
    expect(screen.getByText("Cultivating Soil and Soul")).toBeInTheDocument();
  });

  it("renders every NAV_ITEMS entry in the sidebar", () => {
    renderShell();
    const sidebar = within(screen.getByTestId("sidebar-nav"));
    for (const item of NAV_ITEMS) {
      expect(sidebar.getByText(item.label)).toBeInTheDocument();
    }
  });

  it("renders the first four NAV_ITEMS in the bottom nav and the rest under More", async () => {
    const user = userEvent.setup();
    renderShell();
    const bottomNav = within(screen.getByTestId("bottom-nav"));
    for (const item of NAV_ITEMS.slice(0, 4)) {
      expect(bottomNav.getByText(item.label)).toBeInTheDocument();
    }
    await user.click(bottomNav.getByRole("button", { name: /more/i }));
    for (const item of NAV_ITEMS.slice(4)) {
      expect(bottomNav.getByText(item.label)).toBeInTheDocument();
    }
  });

  it("marks the active nav item with aria-current", () => {
    renderShell("/drafts");
    const sidebar = screen.getByTestId("sidebar-nav");
    const active = sidebar.querySelector('a[aria-current="page"]');
    expect(active).toHaveAttribute("href", "/drafts");
  });

  it("renders an Outlet area for page content", () => {
    renderShell();
    expect(screen.getByTestId("page-content")).toBeInTheDocument();
    expect(screen.getByText("HOME MARKER")).toBeInTheDocument();
  });

  it("shows the pending-approval drafts count as a badge", async () => {
    mockGetDrafts.mockResolvedValue([
      draft(1, "pending_approval"),
      draft(2, "pending_approval"),
      draft(3, "posted"),
    ]);
    renderShell();
    const sidebar = within(screen.getByTestId("sidebar-nav"));
    expect(await sidebar.findByText("2")).toBeInTheDocument();
  });

  it("shows no drafts badge when nothing is pending", async () => {
    mockGetDrafts.mockResolvedValue([draft(1, "posted")]);
    renderShell();
    await screen.findByText("All systems healthy");
    const sidebar = within(screen.getByTestId("sidebar-nav"));
    expect(sidebar.queryByText("0")).not.toBeInTheDocument();
  });

  it("shows the health footer wired to api.getHealth", async () => {
    renderShell();
    expect(await screen.findByText("All systems healthy")).toBeInTheDocument();
    expect(mockGetHealth).toHaveBeenCalled();
  });

  it("shows attention state when a service is down", async () => {
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "postiz", status: "error", message: "down", last_checked: "" },
      ],
      errors: [],
    });
    renderShell();
    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
  });

  it("shows 'All services connected' under the healthy footer", async () => {
    renderShell();
    expect(await screen.findByText("All services connected")).toBeInTheDocument();
    expect(screen.queryByText("Postiz · Claude · Drive")).not.toBeInTheDocument();
  });

  it("shows Checking… with a neutral dot while health loads — never 'All services connected'", async () => {
    mockGetHealth.mockReturnValue(new Promise(() => {}));
    renderShell();
    expect(await screen.findByText("Checking…")).toBeInTheDocument();
    expect(screen.queryByText("All services connected")).not.toBeInTheDocument();
    expect(screen.queryByText("All systems healthy")).not.toBeInTheDocument();
    expect(screen.getByTestId("health-dot")).toHaveClass(
      "bg-[var(--ink-muted)]",
    );
  });

  it("shows Health unavailable with the terra dot when the health query errors", async () => {
    mockGetHealth.mockRejectedValue(new Error("network down"));
    renderShell();
    expect(await screen.findByText("Health unavailable")).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.queryByText("All services connected")).not.toBeInTheDocument();
    expect(screen.queryByText("All systems healthy")).not.toBeInTheDocument();
    expect(screen.getByTestId("health-dot")).toHaveClass("bg-terra-500");
  });

  it("names the unhealthy services in the footer subtitle", async () => {
    mockGetHealth.mockResolvedValue({
      services: [
        { name: "postiz", status: "ok", message: "", last_checked: "" },
        { name: "claude", status: "error", message: "CLI not found", last_checked: "" },
        { name: "oauth", status: "error", message: "token expired", last_checked: "" },
        { name: "sheets", status: "error", message: "unreachable", last_checked: "" },
      ],
      errors: [],
    });
    renderShell();
    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
    expect(
      screen.getByText("Claude · Claude login · Sheets"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Postiz · Claude · Drive")).not.toBeInTheDocument();
  });

  it("links to the Postiz admin", () => {
    renderShell();
    const link = screen.getAllByRole("link", { name: /postiz admin/i })[0];
    expect(link).toHaveAttribute("href", "https://postiz.sethpc.xyz");
  });

  it("calls logout when the sign out button is clicked", async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    renderShell("/", { logout });
    await user.click(screen.getByTestId("sidebar-logout"));
    expect(logout).toHaveBeenCalled();
  });
});

describe("Command palette", () => {
  it("opens with Cmd+K and closes with Escape", async () => {
    const user = userEvent.setup();
    renderShell();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.keyboard("{Meta>}k{/Meta}");
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Type a command or search the farm…"),
    ).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens with Ctrl+K", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("opens when a gv:open-command-palette event is dispatched", async () => {
    // The Dashboard search button dispatches this event instead of
    // prop-drilling an opener through the Outlet.
    renderShell();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new CustomEvent("gv:open-command-palette"));
    });
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("opens from the sidebar search button", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(
      screen.getByRole("button", { name: /search or run command/i }),
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("filters commands by the typed query", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Meta>}k{/Meta}");
    const dialog = within(await screen.findByRole("dialog"));

    expect(dialog.getByText("New post from an idea…")).toBeInTheDocument();
    await user.keyboard("template");
    expect(dialog.getByText("Use a template")).toBeInTheDocument();
    expect(
      dialog.queryByText("New post from an idea…"),
    ).not.toBeInTheDocument();
  });

  it("shows an empty state when nothing matches", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Meta>}k{/Meta}");
    await screen.findByRole("dialog");
    await user.keyboard("zzzznothing");
    expect(screen.getByText("No commands match")).toBeInTheDocument();
  });

  it("navigates to the first match on Enter and closes", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Meta>}k{/Meta}");
    await screen.findByRole("dialog");
    await user.keyboard("Use a template{Enter}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("TEMPLATES MARKER")).toBeInTheDocument();
  });

  it("shows no duplicate 'G <letter>' shortcut hints across Go-to items", async () => {
    // Regression: Today/Templates, Compose/Calendar and Suggestions/Settings
    // all rendered the same "G T"/"G C"/"G S" hint.
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Meta>}k{/Meta}");
    const dialog = within(await screen.findByRole("dialog"));

    const hints = dialog
      .queryAllByText(/^G [A-Z]$/)
      .map((el) => el.textContent);
    expect(new Set(hints).size).toBe(hints.length);
    // colliding first letters carry no hint at all
    expect(dialog.queryByText("G T")).not.toBeInTheDocument();
    expect(dialog.queryByText("G S")).not.toBeInTheDocument();
    // unique first letters keep theirs
    expect(dialog.getByText("G D")).toBeInTheDocument();
  });

  it("navigates when a Go-to row is clicked", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.keyboard("{Meta>}k{/Meta}");
    const dialog = within(await screen.findByRole("dialog"));
    await user.click(dialog.getByRole("button", { name: /drafts/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("DRAFTS MARKER")).toBeInTheDocument();
  });
});
