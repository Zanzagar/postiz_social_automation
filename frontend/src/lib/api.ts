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
    // Do NOT clear the token or redirect — in-progress drafts must survive
    // re-auth. The app listens for this event and shows an inline re-auth UI.
    window.dispatchEvent(new CustomEvent("gv:session-expired"));
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
  require_review: boolean;
  held_at: string | null;
  alt_text: string | null;
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
  color?: string | null;
  target?: number | null;
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
  by_topic: Array<{ topic: string; count: number }>;
  by_pillar: Array<{ pillar: string; count: number }>;
  coverage_gaps: Array<{ title: string; site: string; url: string; fact_count: number }>;
}

export interface KnowledgeEntry {
  id: number;
  fact_type: string;
  content: string;
  topic: string;
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

// --- Media Types ---

export interface MediaItem {
  id: number;
  filename: string;
  local_path: string;
  thumbnail_path: string | null;
  mime_type: string;
  width: number | null;
  height: number | null;
  file_size: number | null;
  pillar: string | null;
  source: string;
  usage_count: number;
  avg_engagement: number;
  created_at: string;
}

export interface MediaBrowseResponse {
  items: MediaItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface MediaTag {
  id: number;
  tag: string;
  confidence: number;
  source: string;
}

export interface MediaUsage {
  content_row_id: number;
  date: string | null;
  status: string;
  pillar: string | null;
}

export interface MediaPerformance {
  id: number;
  platform: string;
  engagement_score: number;
  content_row_id: number | null;
  fetched_at: string;
}

export interface MediaDetailResponse {
  media: MediaItem;
  tags: MediaTag[];
  usage: MediaUsage[];
  performance: MediaPerformance[];
}

export interface MediaBrowseParams {
  tag?: string;
  pillar?: string;
  source?: string;
  sort?: string;
  page?: number;
  per_page?: number;
}

export interface CalendarPlanSlot {
  date: string;
  time: string | null;
  pillar: string | null;
  topic: string | null;
  content_idea: string;
  recommended_media_id: number | null;
  target_platforms: string[];
}

export interface CalendarPlanResponse {
  id: number;
  date_range_start: string;
  date_range_end: string;
  platforms: string[];
  slots: CalendarPlanSlot[];
  status: string;
  created_at: string;
}

export interface Festival {
  name: string;
  date: string;
  significance: string;
  suggested_content_angles: string[];
  topic: string;
  content_pillar: string;
}

export interface MediaSuggestion {
  media_id: number;
  thumbnail_path: string | null;
  filename: string;
  relevance_score: number;
  match_reasons: string[];
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

  // Auto-publish hold / release controls
  holdContent(id: number) {
    return request<ContentRow>(`/api/content/${id}/hold`, { method: "POST" });
  },

  resumeContent(id: number) {
    return request<ContentRow>(`/api/content/${id}/resume`, { method: "POST" });
  },

  setRequireReview(id: number, value: boolean) {
    return request<ContentRow>(`/api/content/${id}/require-review`, {
      method: "PUT",
      body: JSON.stringify({ require_review: value }),
    });
  },

  setAltText(id: number, altText: string) {
    return request<ContentRow>(`/api/content/${id}/alt-text`, {
      method: "PUT",
      body: JSON.stringify({ alt_text: altText }),
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

  revertCaption(contentRowId: number, platform: string, iterationId?: number) {
    const params = new URLSearchParams({
      content_row_id: String(contentRowId),
      platform,
    });
    if (iterationId !== undefined) {
      params.set("iteration_id", String(iterationId));
    }
    return request<IterateResponse>(`/api/iterate/revert?${params}`, {
      method: "POST",
    });
  },

  deleteIteration(iterationId: number) {
    return request<{ ok: boolean }>(`/api/iterations/${iterationId}`, {
      method: "DELETE",
    });
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

  getVoiceRules() {
    return request<{ rules: string[]; summary: string }>("/api/settings/voice-rules");
  },

  updateVoiceRules(rules: string[]) {
    return request<{ rules: string[]; summary: string }>("/api/settings/voice-rules", {
      method: "PUT",
      body: JSON.stringify({ rules }),
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

  browseKnowledge(params: { pillar?: string; topic?: string; fact_type?: string; site?: string; page?: number }) {
    const searchParams = new URLSearchParams();
    if (params.pillar) searchParams.set("pillar", params.pillar);
    if (params.topic) searchParams.set("topic", params.topic);
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

  // Media
  getMedia(params: MediaBrowseParams = {}) {
    const searchParams = new URLSearchParams();
    if (params.tag) searchParams.set("tag", params.tag);
    if (params.pillar) searchParams.set("pillar", params.pillar);
    if (params.source) searchParams.set("source", params.source);
    if (params.sort) searchParams.set("sort", params.sort);
    if (params.page) searchParams.set("page", String(params.page));
    if (params.per_page) searchParams.set("per_page", String(params.per_page));
    return request<MediaBrowseResponse>(`/api/media?${searchParams}`);
  },

  getMediaDetail(id: number) {
    return request<MediaDetailResponse>(`/api/media/${id}`);
  },

  updateMediaTags(id: number, add: string[], remove: string[]) {
    return request<{ tags: MediaTag[] }>(`/api/media/${id}/tags`, {
      method: "PUT",
      body: JSON.stringify({ add, remove }),
    });
  },

  deleteMedia(id: number) {
    return request<{ deleted: boolean; id: number }>(`/api/media/${id}`, {
      method: "DELETE",
    });
  },

  // Drive
  browseDrive(folderId: string, pageToken?: string) {
    const params = new URLSearchParams({ folder_id: folderId });
    if (pageToken) params.set("page_token", pageToken);
    return request<{
      files: Array<{ id: string; name: string; mime_type: string; size: number; thumbnail_link: string | null }>;
      next_page_token: string | null;
    }>(`/api/media/drive/browse?${params}`);
  },

  getMediaHealth() {
    return request<{
      total: number;
      healthy: number;
      drive_refs: number;
      missing_file: Array<{ id: number; filename: string }>;
      missing_thumb: Array<{ id: number; filename: string }>;
      orphan_files: number;
    }>("/api/media-health");
  },

  mediaCleanup(removeMissing: boolean, removeOrphans: boolean) {
    return request<{ removed_entries: number; removed_orphans: number }>(
      `/api/media-cleanup?remove_missing=${removeMissing}&remove_orphans=${removeOrphans}`,
      { method: "POST" },
    );
  },

  getDriveSettings() {
    return request<{ folder_id: string }>("/api/media/drive/settings");
  },

  syncDrive() {
    return request<{ imported: number; skipped: number; errors: Array<{ file_id: string; error: string }> }>(
      "/api/media/drive/sync",
      { method: "POST" },
    );
  },

  importFromDrive(fileIds: string[]) {
    return request<{ imported: number; errors: Array<{ file_id: string; error: string }>; skipped: string[] }>(
      "/api/media/import-drive",
      { method: "POST", body: JSON.stringify({ file_ids: fileIds }) },
    );
  },

  // Calendar Plans
  createCalendarPlan(data: {
    date_range_start: string;
    date_range_end: string;
    platforms: string[];
    constraints?: string;
  }) {
    return request<CalendarPlanResponse>("/api/calendar/plan", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getCalendarPlan(id: number) {
    return request<CalendarPlanResponse>(`/api/calendar/plan/${id}`);
  },

  getCalendarPlans(status?: string) {
    const params = status ? `?status=${status}` : "";
    return request<{ plans: CalendarPlanResponse[] }>(`/api/calendar/plans${params}`);
  },

  approveCalendarPlan(id: number, slotIndices?: number[]) {
    return request<{ created_count: number; content_row_ids: number[] }>(
      `/api/calendar/plan/${id}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ slot_indices: slotIndices ?? null }),
      },
    );
  },

  getFestivals(from?: string, to?: string) {
    const params = new URLSearchParams();
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    return request<Festival[]>(`/api/festivals?${params}`);
  },

  suggestMedia(contentRowId: number) {
    return request<{ suggestions: MediaSuggestion[] }>(
      `/api/media/suggest?content_row_id=${contentRowId}`,
    );
  },

  attachMedia(contentRowId: number, mediaId: number) {
    return request<{ media_catalog_ids: number[] }>(
      `/api/content/${contentRowId}/attach-media?media_id=${mediaId}`,
      { method: "PUT" },
    );
  },

  detachMedia(contentRowId: number, mediaId: number) {
    return request<{ media_catalog_ids: number[] }>(
      `/api/content/${contentRowId}/detach-media?media_id=${mediaId}`,
      { method: "PUT" },
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
 * Parsed SSE event union for POST /api/generate.
 * Sequence: validating -> generating -> zero+ platform_done -> done | error.
 */
export type GenerateStreamEvent =
  | { status: "validating" }
  | { status: "generating" }
  | { status: "platform_done"; platform: string; caption: string }
  | { status: "done"; row_id: number; captions: Record<string, string> }
  | { status: "error"; message: string };

/**
 * Stream caption generation via fetch + ReadableStream.
 * Yields parsed SSE data objects.
 */
export async function* fetchGenerateStream(
  data: GenerateRequest,
): AsyncGenerator<GenerateStreamEvent> {
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
