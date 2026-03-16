import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LoginPage } from "./LoginPage";
import { AuthContext, type AuthContextValue } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/api";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderLogin(overrides: Partial<AuthContextValue> = {}) {
  const auth: AuthContextValue = {
    isAuthenticated: false,
    isLoading: false,
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

  it("renders branding and form", () => {
    renderLogin();
    expect(screen.getByText("Gita Valley")).toBeInTheDocument();
    expect(screen.getByText("Cultivating Soil and Soul")).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("requires password before submitting", async () => {
    const user = userEvent.setup();
    const { auth } = renderLogin();
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("calls login and navigates on success", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockResolvedValue(undefined);
    renderLogin({ login });

    await user.type(screen.getByLabelText(/password/i), "correct-pass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("correct-pass");
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("shows error on incorrect password (401)", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(new ApiError(401, "Incorrect password."));
    renderLogin({ login });

    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Incorrect password.")).toBeInTheDocument();
    });
  });

  it("shows lockout message on rate limit (429)", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(
      new ApiError(429, "Too many failed attempts. Try again in 120 seconds."),
    );
    renderLogin({ login });

    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/too many failed attempts/i)).toBeInTheDocument();
    });
  });

  it("disables form during submission", async () => {
    const user = userEvent.setup();
    // Login that never resolves to keep loading state
    const login = vi.fn().mockReturnValue(new Promise(() => {}));
    renderLogin({ login });

    await user.type(screen.getByLabelText(/password/i), "test");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    });
  });

  it("redirects to / if already authenticated", () => {
    renderLogin({ isAuthenticated: true });
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });
});
