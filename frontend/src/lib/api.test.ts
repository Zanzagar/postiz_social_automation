import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  api,
  ApiError,
  getToken,
  setToken,
  clearToken,
} from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Prevent actual navigation
const locationHrefSpy = vi.spyOn(window, "location", "get");

beforeEach(() => {
  localStorage.clear();
  mockFetch.mockReset();
  locationHrefSpy.mockReturnValue({
    ...window.location,
    href: "http://localhost:3000",
  } as Location);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("token management", () => {
  it("stores and retrieves token from localStorage", () => {
    expect(getToken()).toBeNull();
    setToken("test-jwt");
    expect(getToken()).toBe("test-jwt");
    expect(localStorage.getItem("gv_token")).toBe("test-jwt");
  });

  it("clears token from localStorage", () => {
    setToken("test-jwt");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("api.login", () => {
  it("sends password and returns token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ access_token: "jwt-123", token_type: "bearer" }),
    });

    const result = await api.login("secret");

    expect(mockFetch).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password: "secret" }),
    });
    expect(result.access_token).toBe("jwt-123");
  });

  it("throws ApiError on 401", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Incorrect password." }),
    });

    await expect(api.login("wrong")).rejects.toThrow(ApiError);
  });
});

describe("authenticated requests", () => {
  it("includes Authorization header when token exists", async () => {
    setToken("my-jwt");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    await api.getDrafts();

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer my-jwt");
  });

  it("does not include Authorization header when no token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    await api.getDrafts();

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBeUndefined();
  });

  it("clears token and redirects on 401 response", async () => {
    setToken("expired-jwt");

    // The 401 handler tries to set window.location.href
    // We use a writable mock
    const hrefSetter = vi.fn();
    locationHrefSpy.mockReturnValue({
      ...window.location,
      set href(v: string) {
        hrefSetter(v);
      },
      get href() {
        return "http://localhost:3000";
      },
    } as unknown as Location);

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Invalid or expired token." }),
    });

    await expect(api.getDrafts()).rejects.toThrow(ApiError);
    expect(getToken()).toBeNull();
  });
});

describe("api endpoints use correct paths", () => {
  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  it("getDrafts calls /api/drafts", async () => {
    await api.getDrafts();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/drafts");
  });

  it("getCalendar calls /api/calendar", async () => {
    await api.getCalendar();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar");
  });

  it("getSuggestions calls /api/suggestions with optional status", async () => {
    await api.getSuggestions("approved");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/suggestions?status=approved");
  });

  it("getContentRow calls /api/content/{row}", async () => {
    await api.getContentRow(5);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/5");
  });

  it("editDraft POSTs to /api/drafts/{row}/edit", async () => {
    await api.editDraft(3, { facebook: "caption" });
    expect(mockFetch.mock.calls[0][0]).toBe("/api/drafts/3/edit");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("approveDraft POSTs to /api/drafts/{row}/approve", async () => {
    await api.approveDraft(3);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/drafts/3/approve");
  });

  it("getHealth calls /api/health", async () => {
    await api.getHealth();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/health");
  });

  it("getIntegrations calls /api/integrations", async () => {
    await api.getIntegrations();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/integrations");
  });

  it("uploadFile sends FormData without Content-Type header", async () => {
    const file = new File(["test"], "photo.jpg", { type: "image/jpeg" });
    await api.uploadFile(file);
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.body).toBeInstanceOf(FormData);
    // Content-Type should NOT be set for FormData (browser sets boundary)
    expect(opts.headers["Content-Type"]).toBeUndefined();
  });
});
