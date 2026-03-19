/**
 * Typed API client for the Gita Valley content engine backend.
 * Uses fetch with JWT auth from localStorage.
 * In dev, Vite proxies /api/* to localhost:8000.
 */

const TOKEN_KEY = "gv_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  // Set Content-Type for JSON bodies (not FormData)
  if (options.body && !(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// --- Types ---

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthUser {
  authenticated: boolean;
  sub: string;
}

export interface ContentRow {
  row_number: number;
  date: string;
  content_pillar: string | null;
  raw_text: string;
  media_url: string | null;
  platforms: Record<string, boolean>;
  status: string;
  captions: Record<string, string | null>;
  feedback: string | null;
  postiz_ids: string | null;
  posted_at: string | null;
  error_msg: string | null;
  source: string;
  auto_publish_at: string | null;
}

export interface CalendarEntry {
  row_number: number;
  date: string;
  content_pillar: string | null;
  raw_text: string;
  status: string;
  platforms: Record<string, boolean>;
  captions: Record<string, string | null>;
  source?: string;
}

export interface CalendarResponse {
  entries: CalendarEntry[];
  total: number;
}

export interface Suggestion {
  suggested_date: string;
  content_idea: string;
  suggested_pillar: string;
  rationale: string;
  media_suggestion: string;
  status: string;
}

export interface GenerateRequest {
  raw_text: string;
  media_url?: string | null;
  platforms: string[];
  scheduled_date: string;
  content_pillar?: string | null;
}

export interface RepromptRequest extends GenerateRequest {
  feedback: string;
}

export interface SendToPostizRequest {
  captions: Record<string, string>;
  media_url?: string | null;
  scheduled_at?: string | null;
}

export interface PostizDraftResponse {
  draft_ids: string[];
  platforms: string[];
}

export interface Integration {
  id: string;
  platform: string;
  name: string;
}

export interface ServiceHealth {
  name: string;
  status: string;
  message: string;
  last_checked: string;
}

export interface HealthResponse {
  services: ServiceHealth[];
  errors: Record<string, unknown>[];
}

export interface UploadResponse {
  url: string;
  content_type: string;
  size: number;
}

export interface ApproveResponse {
  success: boolean;
  postiz_ids: string[];
}

// --- Iteration Types ---

export interface IterateRequest {
  content_row_id: number;
  platform: string;
  instruction: string;
  mode?: string;
}

export interface IterateResponse {
  caption: string;
  iteration_id: number;
}

export interface IterationRecord {
  id: number;
  content_row_id: number;
  platform: string;
  old_caption: string | null;
  new_caption: string;
  refinement_instruction: string | null;
  mode: string;
  created_by: number | null;
  created_at: string;
}

// --- Pillar Types ---

export interface Pillar {
  id: number;
  name: string;
  description: string | null;
  color: string | null;
  is_active: boolean;
  sort_order: number;
}

// --- Template Types ---

export interface TemplateVariable {
  name: string;
  type: string;
}

export interface Template {
  id: number;
  name: string;
  pillar: string | null;
  platform_instructions: Record<string, string>;
  raw_text_template: string | null;
  variables: TemplateVariable[];
  schedule_pattern: string | null;
  schedule_time: string | null;
  default_segment_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface CreateTemplateRequest {
  name: string;
  pillar?: string;
  platform_instructions?: Record<string, string>;
  raw_text_template: string;
  variables?: TemplateVariable[];
  schedule_pattern?: string;
  schedule_time?: string;
  default_segment_id?: number;
}

export interface GenerateFromTemplateRequest {
  variable_values: Record<string, string>;
  platforms: string[];
  scheduled_date: string;
  scheduled_time?: string;
}

// --- Publish Config Types ---

export interface PlatformPublishConfig {
  platform: string;
  enabled: boolean;
  delay_hours: number;
  pillar_overrides: Record<string, boolean>;
}

export interface PublishConfigResponse {
  platforms: PlatformPublishConfig[];
}

// --- Analytics Types ---

export interface AnalyticsOverview {
  total_posts: number;
  total_engagement: number;
  avg_engagement: number;
  total_reach: number;
  total_impressions: number;
}

export interface PillarBreakdown {
  pillar: string;
  post_count: number;
  total_engagement: number;
  avg_engagement: number;
  total_reach: number;
}

export interface TopPost {
  id: number;
  pillar: string;
  raw_text: string;
  date: string;
  platform: string;
  engagement: number;
  likes: number;
  comments: number;
  shares: number;
  reach: number;
}

export interface KnowledgeSource {
  name: string;
  type: string;
  page_count?: number;
  post_count?: number;
  last_crawled?: string;
  last_imported?: string;
}

export interface KnowledgeStatusResponse {
  sources: KnowledgeSource[];
  knowledge_entries: number;
}

export interface KnowledgeStats {
  total_pages: number;
  total_knowledge: number;
  pages_with_knowledge: number;
  pages_without_knowledge: number;
  by_type: Array<{ type: string; count: number }>;
  by_pillar: Array<{ pillar: string; count: number }>;
  coverage_gaps: Array<{ title: string; site: string; url: string; fact_count: number }>;
}

export interface KnowledgeEntry {
  id: number;
  fact_type: string;
  content: string;
  pillar: string;
  keywords: string[];
  page_title: string;
  page_url: string;
  site: string;
}

export interface BrowseResponse {
  results: KnowledgeEntry[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface GraphData {
  nodes: Array<{ id: string; label: string; type: string; size: number; site?: string }>;
  links: Array<{ source: string; target: string }>;
}

// --- API Functions ---

export const api = {
  // Auth
  login(password: string) {
    return request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  },

  me() {
    return request<AuthUser>("/api/auth/me");
  },

  // Content
  getDrafts() {
    return request<ContentRow[]>("/api/drafts");
  },

  getCalendar() {
    return request<CalendarResponse>("/api/calendar");
  },

  getSuggestions(status?: string) {
    const params = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<Suggestion[]>(`/api/suggestions${params}`);
  },

  getContentRow(rowNumber: number) {
    return request<ContentRow>(`/api/content/${rowNumber}`);
  },

  editDraft(
    rowNumber: number,
    captions: Record<string, string>,
    platforms?: Record<string, boolean>,
  ) {
    const body: { captions: Record<string, string>; platforms?: Record<string, boolean> } = { captions };
    if (platforms) body.platforms = platforms;
    return request<ContentRow>(`/api/drafts/${rowNumber}/edit`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  approveDraft(rowNumber: number) {
    return request<ApproveResponse>(`/api/drafts/${rowNumber}/approve`, {
      method: "POST",
    });
  },

  // Generation (non-streaming reprompt; generate uses SSE separately)
  reprompt(data: RepromptRequest) {
    return request<{ captions: Record<string, string> }>("/api/reprompt", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Postiz
  sendToPostiz(data: SendToPostizRequest) {
    return request<PostizDraftResponse>("/api/send-to-postiz", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getIntegrations() {
    return request<Integration[]>("/api/integrations");
  },

  // Health
  getHealth() {
    return request<HealthResponse>("/api/health");
  },

  // Upload
  uploadFile(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadResponse>("/api/upload", {
      method: "POST",
      body: formData,
    });
  },

  // Iteration
  iterate(data: IterateRequest) {
    return request<IterateResponse>("/api/iterate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getIterations(contentId: number) {
    return request<IterationRecord[]>(`/api/iterations/${contentId}`);
  },

  // Templates
  getTemplates() {
    return request<Template[]>("/api/templates");
  },

  getTemplate(templateId: number) {
    return request<Template>(`/api/templates/${templateId}`);
  },

  createTemplate(data: CreateTemplateRequest) {
    return request<Template>("/api/templates", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateTemplate(templateId: number, data: CreateTemplateRequest) {
    return request<Template>(`/api/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteTemplate(templateId: number) {
    return request<{ deleted: boolean }>(`/api/templates/${templateId}`, {
      method: "DELETE",
    });
  },

  generateFromTemplate(templateId: number, data: GenerateFromTemplateRequest) {
    return request<ContentRow>(`/api/templates/${templateId}/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  batchGenerateFromTemplate(
    templateId: number,
    data: { variable_values: Record<string, string>; platforms: string[]; weeks: number; scheduled_time?: string },
  ) {
    return request<{ created: number; drafts: ContentRow[] }>(
      `/api/templates/${templateId}/generate-batch`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
  },

  // Pillars
  getPillars(activeOnly = false) {
    const params = activeOnly ? "?active_only=true" : "";
    return request<Pillar[]>(`/api/pillars${params}`);
  },

  createPillar(data: { name: string; description?: string; color?: string; sort_order?: number }) {
    return request<Pillar>("/api/pillars", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updatePillar(id: number, data: { name?: string; description?: string; color?: string; is_active?: boolean; sort_order?: number }) {
    return request<Pillar>(`/api/pillars/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deletePillar(id: number) {
    return request<{ detail: string }>(`/api/pillars/${id}`, {
      method: "DELETE",
    });
  },

  // Publish Config
  getPublishConfig() {
    return request<PublishConfigResponse>("/api/settings/publish");
  },

  updatePublishConfig(platforms: PlatformPublishConfig[]) {
    return request<PublishConfigResponse>("/api/settings/publish", {
      method: "PUT",
      body: JSON.stringify({ platforms }),
    });
  },

  // Analytics
  getAnalyticsOverview() {
    return request<AnalyticsOverview>("/api/analytics/overview");
  },

  getPillarBreakdown() {
    return request<{ pillars: PillarBreakdown[] }>("/api/analytics/pillars");
  },

  getTopPosts(limit = 10) {
    return request<{ posts: TopPost[] }>(`/api/analytics/top-posts?limit=${limit}`);
  },

  // Knowledge
  getKnowledgeStatus() {
    return request<KnowledgeStatusResponse>("/api/knowledge/status");
  },

  triggerCrawl() {
    return request<{ status: string }>("/api/knowledge/crawl", { method: "POST" });
  },

  triggerSocialImport() {
    return request<{ status: string }>("/api/knowledge/import-social", { method: "POST" });
  },

  getKnowledgeStats() {
    return request<KnowledgeStats>("/api/knowledge/stats");
  },

  browseKnowledge(params: { pillar?: string; fact_type?: string; site?: string; page?: number }) {
    const searchParams = new URLSearchParams();
    if (params.pillar) searchParams.set("pillar", params.pillar);
    if (params.fact_type) searchParams.set("fact_type", params.fact_type);
    if (params.site) searchParams.set("site", params.site);
    if (params.page) searchParams.set("page", String(params.page));
    return request<BrowseResponse>(`/api/knowledge/browse?${searchParams}`);
  },

  getKnowledgeGraph() {
    return request<GraphData>("/api/knowledge/graph");
  },

  getCrawlProgress() {
    return request<{ running: boolean; source: string; current: number; total: number; phase: string }>(
      "/api/knowledge/progress",
    );
  },

  searchKnowledge(q: string, pillar?: string) {
    const params = new URLSearchParams({ q });
    if (pillar) params.set("pillar", pillar);
    return request<{ results: Array<{ id: number; fact_type: string; content: string; pillar: string; page_title: string; page_url: string; site: string }>; count: number }>(
      `/api/knowledge/search?${params}`,
    );
  },
};

/**
 * Connect to the SSE generate endpoint.
 * Returns an EventSource that emits JSON messages with {status, captions?, message?}.
 */
/**
 * Note: The backend generate endpoint uses POST + SSE (sse_starlette).
 * Browser EventSource only supports GET, so use fetchGenerateStream() below instead.
 */

/**
 * Stream caption generation via fetch + ReadableStream.
 * Yields parsed SSE data objects.
 */
export async function* fetchGenerateStream(
  data: GenerateRequest,
): AsyncGenerator<{ status: string; captions?: Record<string, string>; message?: string }> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch("/api/generate", {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (!done) {
      buffer += decoder.decode(value, { stream: true });
    }

    const lines = buffer.split("\n");
    buffer = done ? "" : (lines.pop() ?? "");

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(":")) continue;
      if (trimmed.startsWith("data: ")) {
        try {
          yield JSON.parse(trimmed.slice(6));
        } catch {
          // skip malformed data
        }
      }
    }

    if (done) break;
  }
}
