import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  api,
  ApiError,
  getToken,
  setToken,
  clearToken,
  type IterateRequest,
  type IterateResponse,
  type IterationRecord,
  type Template,
  type CreateTemplateRequest,
  type GenerateFromTemplateRequest,
  type PlatformPublishConfig,
  type PublishConfigResponse,
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

// --- Iteration endpoints ---

describe("api.iterate", () => {
  beforeEach(() => {
    setToken("jwt");
  });

  it("POSTs to /api/iterate with correct body", async () => {
    const mockResponse: IterateResponse = { caption: "New caption", iteration_id: 42 };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockResponse),
    });

    const req: IterateRequest = {
      content_row_id: 1,
      platform: "facebook",
      instruction: "Make it shorter",
      mode: "refine",
    };
    const result = await api.iterate(req);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/iterate");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual(req);
    expect(result.caption).toBe("New caption");
    expect(result.iteration_id).toBe(42);
  });
});

describe("api.getIterations", () => {
  beforeEach(() => {
    setToken("jwt");
  });

  it("GETs /api/iterations/{contentId}", async () => {
    const mockIterations: IterationRecord[] = [
      {
        id: 1,
        content_row_id: 5,
        platform: "instagram",
        old_caption: "Old text",
        new_caption: "New text",
        refinement_instruction: "Make it fun",
        mode: "refine",
        created_by: null,
        created_at: "2026-03-17T12:00:00",
      },
    ];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockIterations),
    });

    const result = await api.getIterations(5);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/iterations/5");
    expect(result).toHaveLength(1);
    expect(result[0].platform).toBe("instagram");
  });
});

// --- Template endpoints ---

describe("api templates CRUD", () => {
  const sampleTemplate: Template = {
    id: 1,
    name: "Weekly Update",
    pillar: "spiritual_education",
    platform_instructions: { facebook: "Keep formal" },
    raw_text_template: "This week at {{location}}: {{topic}}",
    variables: [
      { name: "location", type: "text" },
      { name: "topic", type: "text" },
    ],
    schedule_pattern: "weekly",
    schedule_time: null,
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  };

  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(sampleTemplate),
    });
  });

  it("getTemplates GETs /api/templates", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([sampleTemplate]),
    });

    const result = await api.getTemplates();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates");
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Weekly Update");
  });

  it("getTemplate GETs /api/templates/{id}", async () => {
    const result = await api.getTemplate(1);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates/1");
    expect(result.name).toBe("Weekly Update");
  });

  it("createTemplate POSTs to /api/templates", async () => {
    const req: CreateTemplateRequest = {
      name: "Weekly Update",
      pillar: "spiritual_education",
      raw_text_template: "This week: {{topic}}",
      variables: [{ name: "topic", type: "text" }],
    };
    await api.createTemplate(req);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual(req);
  });

  it("updateTemplate PUTs to /api/templates/{id}", async () => {
    const req: CreateTemplateRequest = {
      name: "Updated",
      raw_text_template: "New text",
    };
    await api.updateTemplate(1, req);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates/1");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
  });

  it("deleteTemplate DELETEs /api/templates/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ deleted: true }),
    });

    const result = await api.deleteTemplate(1);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates/1");
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
    expect(result.deleted).toBe(true);
  });

  it("generateFromTemplate POSTs to /api/templates/{id}/generate", async () => {
    // Returns a ContentRow, not a Template
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          row_number: 10,
          date: "2026-03-20",
          raw_text: "Resolved text",
          status: "draft",
        }),
    });

    const req: GenerateFromTemplateRequest = {
      variable_values: { location: "Gita Valley", topic: "Cow Care" },
      platforms: ["facebook", "instagram"],
      scheduled_date: "2026-03-20",
    };
    const result = await api.generateFromTemplate(1, req);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/templates/1/generate");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(result.row_number).toBe(10);
  });
});

// --- Publish config endpoints ---

describe("api publish config", () => {
  const sampleConfig: PublishConfigResponse = {
    platforms: [
      {
        platform: "facebook",
        enabled: true,
        delay_hours: 2,
        pillar_overrides: {},
      },
      {
        platform: "instagram",
        enabled: false,
        delay_hours: 4,
        pillar_overrides: { spiritual_education: true },
      },
    ],
  };

  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(sampleConfig),
    });
  });

  it("getPublishConfig GETs /api/settings/publish", async () => {
    const result = await api.getPublishConfig();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/settings/publish");
    expect(result.platforms).toHaveLength(2);
    expect(result.platforms[0].platform).toBe("facebook");
  });

  it("updatePublishConfig PUTs to /api/settings/publish", async () => {
    const configs: PlatformPublishConfig[] = [
      { platform: "facebook", enabled: true, delay_hours: 1, pillar_overrides: {} },
    ];
    await api.updatePublishConfig(configs);

    expect(mockFetch.mock.calls[0][0]).toBe("/api/settings/publish");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ platforms: configs });
  });
});
