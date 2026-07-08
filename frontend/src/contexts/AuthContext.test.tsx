import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { AuthProvider } from "./AuthContext";
import { LoginError } from "./login-error";
import { useAuth } from "@/hooks/useAuth";
import { getToken, setToken } from "@/lib/api";

// Mock the api module (AuthContext uses api.me; login goes via fetch)
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      login: vi.fn(),
      me: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";
const mockApi = api as unknown as {
  login: ReturnType<typeof vi.fn>;
  me: ReturnType<typeof vi.fn>;
};

const mockFetch = vi.fn();

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

function freshJwt(expiresInSeconds = 3600): string {
  const payload = btoa(
    JSON.stringify({
      sub: "user",
      exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
    }),
  );
  return `header.${payload}.signature`;
}

function TestConsumer() {
  const { isAuthenticated, isLoading, sessionExpired, login, logout } =
    useAuth();
  const [loginError, setLoginError] = useState("");
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="expired">{String(sessionExpired)}</span>
      <span data-testid="login-error">{loginError}</span>
      <button
        onClick={() =>
          login("pass").catch((e: unknown) => {
            if (e instanceof LoginError) {
              setLoginError(`${e.status}:${e.attemptsRemaining}`);
            } else {
              setLoginError("unknown");
            }
          })
        }
        data-testid="login"
      >
        Login
      </button>
      <button onClick={logout} data-testid="logout">
        Logout
      </button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

async function renderAuthenticated() {
  setToken(freshJwt());
  mockApi.me.mockResolvedValue({ authenticated: true, sub: "user" });

  render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>,
  );

  await waitFor(() => {
    expect(screen.getByTestId("auth").textContent).toBe("true");
  });
}

describe("AuthProvider", () => {
  it("starts unauthenticated when no token exists", async () => {
    mockApi.me.mockRejectedValue(new Error("no token"));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("auth").textContent).toBe("false");
  });

  it("validates existing token on mount", async () => {
    setToken(freshJwt());
    mockApi.me.mockResolvedValue({ authenticated: true, sub: "user" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("auth").textContent).toBe("true");
    expect(mockApi.me).toHaveBeenCalled();
  });

  it("clears expired token on mount", async () => {
    setToken(freshJwt(-3600));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("auth").textContent).toBe("false");
    expect(getToken()).toBeNull();
    // Should not call me() for expired tokens
    expect(mockApi.me).not.toHaveBeenCalled();
  });

  it("login posts to /api/auth/login, stores token, and authenticates", async () => {
    mockApi.me.mockRejectedValue(new Error("no token"));
    mockFetch.mockResolvedValue(
      jsonResponse(200, { access_token: "new-jwt", token_type: "bearer" }),
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByTestId("login"));
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ password: "pass" }),
      }),
    );
    expect(screen.getByTestId("auth").textContent).toBe("true");
    expect(getToken()).toBe("new-jwt");
  });

  it("login surfaces attempts_remaining from a 401 detail object", async () => {
    mockApi.me.mockRejectedValue(new Error("no token"));
    mockFetch.mockResolvedValue(
      jsonResponse(401, {
        detail: { message: "invalid_password", attempts_remaining: 2 },
      }),
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByTestId("login"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("login-error").textContent).toBe("401:2");
    });
  });

  it("login tolerates a plain-string 401 detail (no attempts info)", async () => {
    mockApi.me.mockRejectedValue(new Error("no token"));
    mockFetch.mockResolvedValue(
      jsonResponse(401, { detail: "Incorrect password." }),
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByTestId("login"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("login-error").textContent).toBe("401:null");
    });
  });

  it("logout clears token and sets unauthenticated", async () => {
    await renderAuthenticated();

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByTestId("logout"));
    });

    expect(screen.getByTestId("auth").textContent).toBe("false");
    expect(getToken()).toBeNull();
  });
});

describe("session expiry", () => {
  it("shows the re-auth overlay on gv:session-expired without unmounting routes", async () => {
    await renderAuthenticated();

    act(() => {
      window.dispatchEvent(new CustomEvent("gv:session-expired"));
    });

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Your session rested.");
    expect(dialog).toHaveTextContent(
      "Your draft is safe on this device — sign back in to pick it up.",
    );
    // Routes (children) stay mounted and auth is NOT cleared
    expect(screen.getByTestId("auth").textContent).toBe("true");
    expect(screen.getByTestId("expired").textContent).toBe("true");
    expect(getToken()).not.toBeNull();
  });

  it("resume flow re-authenticates and hides the overlay", async () => {
    await renderAuthenticated();

    act(() => {
      window.dispatchEvent(new CustomEvent("gv:session-expired"));
    });
    await screen.findByRole("dialog");

    mockFetch.mockResolvedValue(
      jsonResponse(200, { access_token: "resumed-jwt", token_type: "bearer" }),
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Farm password"), "farm-pass");
    await user.click(
      screen.getByRole("button", { name: "Resume where I left off" }),
    );

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ password: "farm-pass" }),
      }),
    );
    expect(getToken()).toBe("resumed-jwt");
    expect(screen.getByTestId("expired").textContent).toBe("false");
    expect(screen.getByTestId("auth").textContent).toBe("true");
  });

  it("shows an error inside the overlay when resume fails", async () => {
    await renderAuthenticated();

    act(() => {
      window.dispatchEvent(new CustomEvent("gv:session-expired"));
    });
    await screen.findByRole("dialog");

    mockFetch.mockResolvedValue(
      jsonResponse(401, {
        detail: { message: "invalid_password", attempts_remaining: 3 },
      }),
    );

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Farm password"), "nope");
    await user.click(
      screen.getByRole("button", { name: "Resume where I left off" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Incorrect password.");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("proactively detects token expiry via the interval check", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-07-06T10:00:00Z"));

    setToken(freshJwt(3600));
    mockApi.me.mockResolvedValue({ authenticated: true, sub: "user" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("auth").textContent).toBe("true");
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // Jump past the 1-hour token expiry; the 30s check should catch it
    act(() => {
      vi.advanceTimersByTime(3630 * 1000);
    });

    expect(screen.getByRole("dialog")).toHaveTextContent(
      "Your session rested.",
    );
    expect(screen.getByTestId("auth").textContent).toBe("true");
  });
});

describe("useAuth outside provider", () => {
  it("throws when used outside AuthProvider", () => {
    // Suppress console.error for the expected error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<TestConsumer />)).toThrow(
      "useAuth must be used within an AuthProvider",
    );

    spy.mockRestore();
  });
});
