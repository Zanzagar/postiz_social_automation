import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "@/hooks/useAuth";
import { getToken, setToken } from "@/lib/api";

// Mock the api module
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

function TestConsumer() {
  const { isAuthenticated, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <button onClick={() => login("pass")} data-testid="login">
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
});

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
    // Create a non-expired JWT payload
    const payload = btoa(JSON.stringify({ sub: "user", exp: Math.floor(Date.now() / 1000) + 3600 }));
    setToken(`header.${payload}.signature`);

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
    // Expired JWT
    const payload = btoa(JSON.stringify({ sub: "user", exp: Math.floor(Date.now() / 1000) - 3600 }));
    setToken(`header.${payload}.signature`);

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

  it("login stores token and sets authenticated", async () => {
    mockApi.me.mockRejectedValue(new Error("no token"));
    mockApi.login.mockResolvedValue({ access_token: "new-jwt", token_type: "bearer" });

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

    expect(screen.getByTestId("auth").textContent).toBe("true");
    expect(getToken()).toBe("new-jwt");
  });

  it("logout clears token and sets unauthenticated", async () => {
    // Start authenticated
    const payload = btoa(JSON.stringify({ sub: "user", exp: Math.floor(Date.now() / 1000) + 3600 }));
    setToken(`header.${payload}.signature`);
    mockApi.me.mockResolvedValue({ authenticated: true, sub: "user" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth").textContent).toBe("true");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByTestId("logout"));
    });

    expect(screen.getByTestId("auth").textContent).toBe("false");
    expect(getToken()).toBeNull();
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
