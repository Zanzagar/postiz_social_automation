import { LoginError } from "./login-error";
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken, clearToken } from "@/lib/api";
import { SessionExpiryOverlay } from "@/components/auth/SessionExpiryOverlay";

/** How often we proactively check the JWT for expiry (ms). */
const TOKEN_CHECK_INTERVAL_MS = 30_000;

export interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  /**
   * True when the 1-hour token has lapsed mid-work. Routes stay mounted.
   * Optional so existing test fixtures that build this value stay valid;
   * AuthProvider always supplies it.
   */
  sessionExpired?: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);


function extractDetail(body: unknown): unknown {
  if (body && typeof body === "object" && "detail" in body) {
    return (body as { detail: unknown }).detail;
  }
  return null;
}

async function loginRequest(password: string): Promise<string> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

  if (res.ok) {
    const data = (await res.json()) as { access_token: string };
    return data.access_token;
  }

  const detail = extractDetail(await res.json().catch(() => null));

  if (res.status === 401) {
    // Detail may be {"message": "invalid_password", "attempts_remaining": N}
    // or a plain string from older backends — parse defensively.
    let attemptsRemaining: number | null = null;
    if (detail && typeof detail === "object" && "attempts_remaining" in detail) {
      const n = (detail as { attempts_remaining: unknown }).attempts_remaining;
      if (typeof n === "number" && Number.isFinite(n)) {
        attemptsRemaining = n;
      }
    }
    throw new LoginError(401, "Incorrect password.", { attemptsRemaining });
  }

  if (res.status === 429) {
    // Detail: "Too many failed attempts. Try again in N seconds."
    const text = typeof detail === "string" ? detail : "";
    const match = /(\d+)\s*second/.exec(text);
    throw new LoginError(429, text || "Too many failed attempts.", {
      retrySeconds: match ? Number(match[1]) : 300,
    });
  }

  const message =
    typeof detail === "string" && detail
      ? detail
      : `Login failed (${res.status}).`;
  throw new LoginError(res.status, message);
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Check existing token on mount
  useEffect(() => {
    const token = getToken();
    if (!token || isTokenExpired(token)) {
      clearToken();
      setIsAuthenticated(false);
      setIsLoading(false);
      return;
    }

    // Validate token with backend
    api
      .me()
      .then(() => setIsAuthenticated(true))
      .catch(() => {
        clearToken();
        setIsAuthenticated(false);
      })
      .finally(() => setIsLoading(false));
  }, []);

  // api.ts dispatches this on any 401 — mark expired WITHOUT clearing auth
  // so routes stay mounted and unsaved drafts survive re-auth.
  useEffect(() => {
    const onExpired = () => setSessionExpired(true);
    window.addEventListener("gv:session-expired", onExpired);
    return () => window.removeEventListener("gv:session-expired", onExpired);
  }, []);

  // Proactive expiry check — show the re-auth overlay without waiting for a
  // failed API call.
  useEffect(() => {
    if (!isAuthenticated) return;
    const id = window.setInterval(() => {
      const token = getToken();
      if (!token || isTokenExpired(token)) {
        setSessionExpired(true);
      }
    }, TOKEN_CHECK_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [isAuthenticated]);

  const login = useCallback(async (password: string) => {
    const accessToken = await loginRequest(password);
    setToken(accessToken);
    setIsAuthenticated(true);
    setSessionExpired(false);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setIsAuthenticated(false);
    setSessionExpired(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, isLoading, sessionExpired, login, logout }),
    [isAuthenticated, isLoading, sessionExpired, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      {isAuthenticated && sessionExpired && (
        <SessionExpiryOverlay onResume={login} />
      )}
    </AuthContext.Provider>
  );
}
