import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";
import { AuthContext, type AuthContextValue } from "@/contexts/AuthContext";
import { LoginError } from "@/contexts/login-error";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderLogin(overrides: Partial<AuthContextValue> = {}) {
  const auth: AuthContextValue = {
    isAuthenticated: false,
    isLoading: false,
    sessionExpired: false,
    login: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
  return {
    auth,
    ...render(
      <BrowserRouter>
        <AuthContext.Provider value={auth}>
          <LoginPage />
        </AuthContext.Provider>
      </BrowserRouter>,
    ),
  };
}

describe("LoginPage", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the gate: branding, form, and divider notes", () => {
    renderLogin();
    expect(screen.getByText("Gita Valley")).toBeInTheDocument();
    expect(screen.getByText("Cultivating Soil and Soul")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Welcome back to the pasture" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Farm password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open the gate" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Port Royal, Pennsylvania")).toBeInTheDocument();
    expect(
      screen.getByText(/named accounts arrive with Phase 4/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Unsaved drafts stay safe on this device/i),
    ).toBeInTheDocument();
  });

  it("requires password before submitting", async () => {
    const user = userEvent.setup();
    const { auth } = renderLogin();
    await user.click(screen.getByRole("button", { name: "Open the gate" }));
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("calls login and navigates on success", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockResolvedValue(undefined);
    renderLogin({ login });

    await user.type(screen.getByLabelText("Farm password"), "correct-pass");
    await user.click(screen.getByRole("button", { name: "Open the gate" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("correct-pass");
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("shows attempts remaining on wrong password", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(
      new LoginError(401, "Incorrect password.", { attemptsRemaining: 4 }),
    );
    renderLogin({ login });

    await user.type(screen.getByLabelText("Farm password"), "molasses");
    await user.click(screen.getByRole("button", { name: "Open the gate" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "That's not it — 4 tries remaining before the gate rests.",
    );
    expect(screen.getByLabelText("Farm password")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("does not crash when the 401 carries no attempts count", async () => {
    const user = userEvent.setup();
    const login = vi
      .fn()
      .mockRejectedValue(new LoginError(401, "Incorrect password."));
    renderLogin({ login });

    await user.type(screen.getByLabelText("Farm password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Open the gate" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("That's not it — try again.");
  });

  it("shows the resting-gate lockout card with a live countdown", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-07-06T10:00:00Z"));

    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(
      new LoginError(429, "Too many failed attempts. Try again in 277 seconds.", {
        retrySeconds: 277,
      }),
    );
    renderLogin({ login });

    await user.type(screen.getByLabelText("Farm password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Open the gate" }));

    expect(
      await screen.findByText("Too many tries — the gate is resting."),
    ).toBeInTheDocument();
    expect(screen.getByText("4:37")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open the gate" }),
    ).toBeDisabled();
    expect(screen.getByLabelText("Farm password")).toBeDisabled();

    // One minute later the countdown has ticked down
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByText("3:37")).toBeInTheDocument();

    // After the full lockout window the gate reopens
    act(() => {
      vi.advanceTimersByTime(4 * 60_000);
    });
    expect(
      screen.queryByText("Too many tries — the gate is resting."),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Farm password")).not.toBeDisabled();
  });

  it("disables the submit button during submission", async () => {
    const user = userEvent.setup();
    // Login that never resolves to keep loading state
    const login = vi.fn().mockReturnValue(new Promise(() => {}));
    renderLogin({ login });

    await user.type(screen.getByLabelText("Farm password"), "test");
    await user.click(screen.getByRole("button", { name: "Open the gate" }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Open the gate" }),
      ).toBeDisabled();
    });
  });

  it("redirects to / if already authenticated", () => {
    renderLogin({ isAuthenticated: true });
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });
});
