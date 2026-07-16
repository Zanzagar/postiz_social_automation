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

  it("dispatches gv:session-expired and keeps the token on 401 response", async () => {
    setToken("expired-jwt");

    const expiredListener = vi.fn();
    window.addEventListener("gv:session-expired", expiredListener);

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Invalid or expired token." }),
    });

    await expect(api.getDrafts()).rejects.toThrow(ApiError);

    // Token is preserved so in-progress drafts survive re-auth
    expect(getToken()).toBe("expired-jwt");
    expect(expiredListener).toHaveBeenCalledTimes(1);

    window.removeEventListener("gv:session-expired", expiredListener);
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

  it("holdContent POSTs to /api/content/{id}/hold", async () => {
    await api.holdContent(7);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/7/hold");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("resumeContent POSTs to /api/content/{id}/resume", async () => {
    await api.resumeContent(7);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/7/resume");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("setRequireReview PUTs to /api/content/{id}/require-review", async () => {
    await api.setRequireReview(7, true);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/7/require-review");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ require_review: true });
  });

  it("setAltText PUTs to /api/content/{id}/alt-text", async () => {
    await api.setAltText(7, "A cow grazing at dawn");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/7/alt-text");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      alt_text: "A cow grazing at dawn",
    });
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

// --- Phase 2: suggestions, analytics v2, hashtags, knowledge ask ---

describe("phase 2 endpoints use correct paths", () => {
  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  it("refreshSuggestions POSTs to /api/suggestions/refresh", async () => {
    await api.refreshSuggestions();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/suggestions/refresh");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("dismissSuggestion POSTs to /api/suggestions/{id}/dismiss", async () => {
    await api.dismissSuggestion(7);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/suggestions/7/dismiss");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("draftSuggestion POSTs to /api/suggestions/{id}/draft", async () => {
    await api.draftSuggestion(7);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/suggestions/7/draft");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("getAnalyticsSummary defaults to range=30d", async () => {
    await api.getAnalyticsSummary();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/analytics/summary?range=30d");
  });

  it("getAnalyticsPosts passes range, limit and offset", async () => {
    await api.getAnalyticsPosts("90d", 10, 20);
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/analytics/posts?range=90d&limit=10&offset=20",
    );
  });

  it("getAnalyticsPillarInsights calls /api/analytics/pillar-insights", async () => {
    await api.getAnalyticsPillarInsights();
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/analytics/pillar-insights?range=30d",
    );
  });

  it("getAnalyticsPlatforms calls /api/analytics/platforms", async () => {
    await api.getAnalyticsPlatforms("7d");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/analytics/platforms?range=7d");
  });

  it("getAnalyticsRhythm calls /api/analytics/rhythm", async () => {
    await api.getAnalyticsRhythm();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/analytics/rhythm?range=30d");
  });

  it("syncAnalytics POSTs to /api/analytics/sync", async () => {
    await api.syncAnalytics();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/analytics/sync");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("getHashtagSuggestions passes count and optional platform", async () => {
    await api.getHashtagSuggestions();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/analytics/hashtags?count=8");

    await api.getHashtagSuggestions("instagram", 5);
    expect(mockFetch.mock.calls[1][0]).toBe(
      "/api/analytics/hashtags?count=5&platform=instagram",
    );
  });

  it("askKnowledge POSTs the question to /api/knowledge/ask", async () => {
    await api.askKnowledge("When is Janmashtami?");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/knowledge/ask");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      question: "When is Janmashtami?",
    });
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

// --- Phase 3: media catalog endpoints ---

describe("media catalog endpoints", () => {
  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  it("getMedia GETs /api/media with empty query and auth header by default", async () => {
    await api.getMedia();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media?");
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer jwt");
  });

  it("getMedia serializes all filter params including q, media_type, untagged", async () => {
    await api.getMedia({
      tag: "cows",
      pillar: "farm",
      source: "upload",
      q: "sunset barn",
      media_type: "image",
      untagged: true,
      sort: "date",
      page: 2,
      per_page: 30,
    });
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/media?tag=cows&pillar=farm&source=upload&q=sunset+barn&media_type=image&untagged=true&sort=date&page=2&per_page=30",
    );
  });

  it("getMedia omits untagged from the query when false", async () => {
    await api.getMedia({ untagged: false });
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media?");
  });

  it("getMedia returns the browse response with storage_used_bytes", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          items: [],
          total: 0,
          page: 1,
          per_page: 30,
          total_pages: 0,
          storage_used_bytes: 1234,
        }),
    });
    const result = await api.getMedia();
    expect(result.storage_used_bytes).toBe(1234);
  });

  it("getMediaDetail GETs /api/media/{id}", async () => {
    await api.getMediaDetail(9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9");
  });

  it("updateMedia PATCHes /api/media/{id} preserving explicit nulls", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 9, alt_text: null, season: "fall" }),
    });
    const result = await api.updateMedia(9, { alt_text: null, season: "fall" });
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9");
    expect(mockFetch.mock.calls[0][1].method).toBe("PATCH");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      alt_text: null,
      season: "fall",
    });
    expect(result.season).toBe("fall");
  });

  it("updateMedia omits absent fields from the PATCH body", async () => {
    await api.updateMedia(9, { default_caption: "Calves at dawn" });
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      default_caption: "Calves at dawn",
    });
  });

  it("getAdaptedVersions GETs /api/media/{id}/adapted", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          adapted: [
            {
              id: 1,
              platform: "instagram",
              format: "post",
              adapted_path: "media/adapted/9_instagram_post.jpg",
              width: 1080,
              height: 1080,
              has_text_overlay: false,
              created_at: "2026-07-01T00:00:00",
            },
          ],
        }),
    });
    const result = await api.getAdaptedVersions(9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9/adapted");
    expect(result.adapted).toHaveLength(1);
    expect(result.adapted[0].platform).toBe("instagram");
  });

  it("adaptMedia POSTs platforms and formats to /api/media/{id}/adapt", async () => {
    await api.adaptMedia(9, ["instagram", "facebook"], ["post", "story"]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9/adapt");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      platforms: ["instagram", "facebook"],
      formats: ["post", "story"],
    });
  });

  it("generateMediaMeta POSTs to /api/media/{id}/generate-meta", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          alt_text: "A cow grazing in the morning pasture.",
          season: "summer",
          suggested_tags: [{ tag: "cows", confidence: 0.9 }],
        }),
    });
    const result = await api.generateMediaMeta(9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9/generate-meta");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(result.alt_text).toBe("A cow grazing in the morning pasture.");
    expect(result.suggested_tags[0].tag).toBe("cows");
  });

  it("uploadMediaFile POSTs FormData field 'file' to /api/media/upload", async () => {
    const file = new File(["img"], "cow.jpg", { type: "image/jpeg" });
    await api.uploadMediaFile(file);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/upload");
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("POST");
    expect(opts.body).toBeInstanceOf(FormData);
    expect(opts.body.get("file")).toBe(file);
    // Content-Type must NOT be set for FormData (browser sets boundary)
    expect(opts.headers["Content-Type"]).toBeUndefined();
    expect(opts.headers["Authorization"]).toBe("Bearer jwt");
  });

  it("importMediaUrl POSTs the url to /api/media/import-url", async () => {
    await api.importMediaUrl("https://example.org/cow.jpg");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/import-url");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      url: "https://example.org/cow.jpg",
    });
  });

  it("updateMediaTags PUTs add/remove to /api/media/{id}/tags", async () => {
    await api.updateMediaTags(9, ["cow"], ["barn"]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9/tags");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      add: ["cow"],
      remove: ["barn"],
    });
  });

  it("deleteMedia DELETEs /api/media/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ deleted: true, id: 9 }),
    });
    const result = await api.deleteMedia(9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/9");
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
    expect(result.deleted).toBe(true);
  });

  it("suggestMedia GETs /api/media/suggest with content_row_id", async () => {
    await api.suggestMedia(12);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/suggest?content_row_id=12");
  });

  it("attachMedia PUTs to /api/content/{row}/attach-media with media_id query", async () => {
    await api.attachMedia(3, 9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/3/attach-media?media_id=9");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
  });

  it("detachMedia PUTs to /api/content/{row}/detach-media with media_id query", async () => {
    await api.detachMedia(3, 9);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/content/3/detach-media?media_id=9");
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
  });

  it("getMediaHealth GETs /api/media-health", async () => {
    await api.getMediaHealth();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media-health");
  });

  it("mediaCleanup POSTs /api/media-cleanup with both flags", async () => {
    await api.mediaCleanup(true, false);
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/media-cleanup?remove_missing=true&remove_orphans=false",
    );
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });
});

// --- Phase 3: drive endpoints ---

describe("drive endpoints", () => {
  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  it("browseDrive GETs /api/media/drive/browse with folder_id", async () => {
    await api.browseDrive("folder-1");
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/media/drive/browse?folder_id=folder-1",
    );
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer jwt");
  });

  it("browseDrive passes page_token when provided", async () => {
    await api.browseDrive("folder-1", "tok-2");
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/media/drive/browse?folder_id=folder-1&page_token=tok-2",
    );
  });

  it("importFromDrive POSTs file_ids to /api/media/import-drive", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ imported: 2, errors: [], skipped: [] }),
    });
    const result = await api.importFromDrive(["a", "b"]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/import-drive");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      file_ids: ["a", "b"],
    });
    expect(result.imported).toBe(2);
  });

  it("syncDrive POSTs to /api/media/drive/sync", async () => {
    await api.syncDrive();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/drive/sync");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("getDriveSettings GETs /api/media/drive/settings", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ folder_id: "f-1" }),
    });
    const result = await api.getDriveSettings();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/media/drive/settings");
    expect(result.folder_id).toBe("f-1");
  });
});

// --- Phase 3: calendar plan endpoints ---

describe("calendar plan endpoints", () => {
  const samplePlan = {
    id: 1,
    date_range_start: "2026-07-20",
    date_range_end: "2026-07-27",
    platforms: ["facebook"],
    slots: [],
    status: "draft",
    created_at: "2026-07-15T10:00:00",
  };

  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(samplePlan),
    });
  });

  it("createCalendarPlan POSTs to /api/calendar/plan with the full body", async () => {
    const req = {
      date_range_start: "2026-07-20",
      date_range_end: "2026-07-27",
      platforms: ["facebook"],
      constraints: "2 posts per week",
    };
    const result = await api.createCalendarPlan(req);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plan");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual(req);
    expect(result.status).toBe("draft");
  });

  it("getCalendarPlan GETs /api/calendar/plan/{id}", async () => {
    const result = await api.getCalendarPlan(1);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plan/1");
    expect(result.id).toBe(1);
  });

  it("getCalendarPlans GETs /api/calendar/plans without status", async () => {
    await api.getCalendarPlans();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plans");
  });

  it("getCalendarPlans passes the status filter", async () => {
    await api.getCalendarPlans("draft");
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plans?status=draft");
  });

  it("approveCalendarPlan POSTs slot_indices to /api/calendar/plan/{id}/approve", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ created_count: 2, content_row_ids: [10, 11] }),
    });
    const result = await api.approveCalendarPlan(1, [0, 2]);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plan/1/approve");
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      slot_indices: [0, 2],
    });
    expect(result.created_count).toBe(2);
  });

  it("approveCalendarPlan sends slot_indices null when omitted", async () => {
    await api.approveCalendarPlan(1);
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({
      slot_indices: null,
    });
  });

  it("deleteCalendarPlan DELETEs /api/calendar/plan/{id}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ deleted: true, id: 1 }),
    });
    const result = await api.deleteCalendarPlan(1);
    expect(mockFetch.mock.calls[0][0]).toBe("/api/calendar/plan/1");
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
    expect(result.deleted).toBe(true);
  });
});

// --- Phase 3: festival endpoints ---

describe("festival endpoints", () => {
  beforeEach(() => {
    setToken("jwt");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });
  });

  it("getFestivals GETs /api/festivals with empty query by default", async () => {
    await api.getFestivals();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/festivals?");
  });

  it("getFestivals passes from and to", async () => {
    await api.getFestivals("2026-07-01", "2026-08-01");
    expect(mockFetch.mock.calls[0][0]).toBe(
      "/api/festivals?from=2026-07-01&to=2026-08-01",
    );
  });
});
