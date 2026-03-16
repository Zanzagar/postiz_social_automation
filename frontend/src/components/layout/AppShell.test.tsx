import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { AuthContext, type AuthContextValue } from "@/contexts/AuthContext";

const mockAuth: AuthContextValue = {
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
};

function renderShell(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthContext.Provider value={mockAuth}>
        <AppShell />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("renders sidebar with branding", () => {
    renderShell();
    expect(screen.getByText("Gita Valley")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    renderShell();
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Create").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Drafts").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Calendar").length).toBeGreaterThanOrEqual(1);
  });

  it("highlights active nav item", () => {
    renderShell("/drafts");
    // The sidebar link for Drafts should have active styling
    const sidebarNav = screen.getByTestId("sidebar-nav");
    const draftsLink = sidebarNav.querySelector('a[href="/drafts"]');
    expect(draftsLink).toHaveAttribute("data-active", "true");
  });

  it("renders bottom nav for mobile", () => {
    renderShell();
    expect(screen.getByTestId("bottom-nav")).toBeInTheDocument();
  });

  it("renders an Outlet area for page content", () => {
    renderShell();
    expect(screen.getByTestId("page-content")).toBeInTheDocument();
  });

  it("calls logout when logout button clicked", async () => {
    const user = userEvent.setup();
    const logout = vi.fn();
    render(
      <MemoryRouter>
        <AuthContext.Provider value={{ ...mockAuth, logout }}>
          <AppShell />
        </AuthContext.Provider>
      </MemoryRouter>,
    );
    const logoutBtn = screen.getByTestId("sidebar-logout");
    await user.click(logoutBtn);
    expect(logout).toHaveBeenCalled();
  });
});
