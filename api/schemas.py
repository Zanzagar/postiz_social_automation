"""Pydantic response/request schemas for the API."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# --- Content ---


class ContentRowResponse(BaseModel):
    """JSON-serializable content row."""

    row_number: int
    date: datetime
    content_pillar: str | None = None
    raw_text: str
    media_url: str | None = None
    platforms: dict[str, bool]
    status: str
    captions: dict[str, str | None]
    feedback: str | None = None
    postiz_ids: str | None = None
    posted_at: datetime | None = None
    error_msg: str | None = None
    source: str = "staff"
    auto_publish_at: datetime | None = None
    require_review: bool = False
    held_at: datetime | None = None
    alt_text: str | None = None


class SuggestionItem(BaseModel):
    """A single content suggestion (festival, pillar gap, or template reminder)."""

    id: int
    type: str
    title: str
    note: str
    pillar: str | None = None
    date: str | None = None  # YYYY-MM-DD
    days_until: int | None = None  # date - today; negative if past
    status: str


class SuggestionsResponse(BaseModel):
    """Envelope for suggestion lists."""

    suggestions: list[SuggestionItem]


class SuggestionDismissResponse(BaseModel):
    """Result of dismissing a suggestion."""

    id: int
    status: str


class SuggestionDraftResponse(BaseModel):
    """Result of drafting a suggestion into a content row."""

    id: int
    status: str
    content_row_id: int


class CalendarEntry(BaseModel):
    """A content row grouped for calendar display."""

    row_number: int
    date: datetime
    content_pillar: str | None = None
    raw_text: str
    status: str
    platforms: dict[str, bool]
    captions: dict[str, str | None]


class CalendarResponse(BaseModel):
    """Calendar data with entries grouped by date."""

    entries: list[CalendarEntry]
    total: int


# --- Generation ---


class GenerateRequest(BaseModel):
    raw_text: str = Field(max_length=5000)
    media_url: str | None = None
    platforms: list[str]
    scheduled_date: str
    content_pillar: str | None = None


class RepromptRequest(BaseModel):
    raw_text: str = Field(max_length=5000)
    media_url: str | None = None
    platforms: list[str]
    scheduled_date: str
    feedback: str = Field(max_length=2000)


# --- Postiz ---


class SendToPostizRequest(BaseModel):
    captions: dict[str, str]
    media_url: str | None = None
    scheduled_at: str | None = None


class PostizDraftResponse(BaseModel):
    draft_ids: list[str]
    platforms: list[str]


class IntegrationResponse(BaseModel):
    id: str
    platform: str
    name: str


# --- Health ---


class ServiceHealth(BaseModel):
    name: str
    status: str
    message: str
    last_checked: datetime


class HealthResponse(BaseModel):
    services: list[ServiceHealth]
    errors: list[dict]


# --- Upload ---


class UploadResponse(BaseModel):
    url: str
    content_type: str
    size: int


# --- Actions ---


class ApproveResponse(BaseModel):
    success: bool
    postiz_ids: list[str]


class PlatformPublishResult(BaseModel):
    """Outcome of one platform's publish attempt (shared loop/manual core).

    ``link`` is Postiz's releaseURL when the API returns one — never
    fabricated our side. ``already_published`` marks platforms that were
    published on an earlier attempt (reported from the stored postiz_ids
    map, no new Postiz call) so the UI can render their final state instead
    of dropping them.
    """

    platform: str
    status: str  # "posted" | "scheduled" | "failed"
    postiz_id: str | None = None
    error: str | None = None
    link: str | None = None
    already_published: bool = False


class PublishNowResponse(BaseModel):
    """Result of POST /api/content/{row_id}/publish-now."""

    row_id: int
    results: list[PlatformPublishResult]
    status: str
    posted_at: datetime | None = None


class EditCaptionsRequest(BaseModel):
    captions: dict[str, str]
    platforms: dict[str, bool] | None = None


class RequireReviewRequest(BaseModel):
    require_review: bool


class AltTextRequest(BaseModel):
    alt_text: str = Field(max_length=2000)


# --- Pillars ---


class PillarResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    color: str | None = None
    is_active: bool = True
    sort_order: int = 0
    target_distribution: float | None = None
    target: int | None = None  # percent, derived from target_distribution


class PillarCreateRequest(BaseModel):
    name: str
    description: str | None = None
    color: str | None = None
    sort_order: int = 0
    target_distribution: float | None = None


class PillarUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    target_distribution: float | None = None


# --- Calendar Plans ---


class CalendarPlanSlot(BaseModel):
    date: str
    time: str | None = None
    pillar: str | None = None
    topic: str | None = None
    content_idea: str
    recommended_media_id: int | None = None
    target_platforms: list[str] = []


class CalendarPlanCreate(BaseModel):
    date_range_start: str
    date_range_end: str
    platforms: list[str] = []
    constraints: str | None = None


class CalendarPlanResponse(BaseModel):
    id: int
    date_range_start: str
    date_range_end: str
    platforms: list[str]
    slots: list[CalendarPlanSlot]
    status: str
    created_at: str


# --- Publish Config ---


class PlatformPublishConfig(BaseModel):
    platform: str
    enabled: bool = False
    delay_hours: int = 2
    pillar_overrides: dict[str, bool] = {}


class PublishConfigResponse(BaseModel):
    platforms: list[PlatformPublishConfig]


class UpdatePublishConfigRequest(BaseModel):
    platforms: list[PlatformPublishConfig]


# --- Brand Settings ---


class BrandSettingsResponse(BaseModel):
    """All brand settings as a flat dict."""

    brand_name: str = ""
    tagline: str = ""
    website: str = ""
    key_claim: str = ""
    products: str = ""
    voice_description: str = ""

    model_config = {"extra": "allow"}


class BrandSettingsUpdate(BaseModel):
    """Partial update — only provided keys are changed."""

    model_config = {"extra": "allow"}


# --- Templates ---


class TemplateVariable(BaseModel):
    name: str
    type: str = "text"


class TemplateCreateRequest(BaseModel):
    name: str
    pillar: str | None = None
    platform_instructions: dict[str, str] = {}
    raw_text_template: str
    variables: list[TemplateVariable] = []
    schedule_pattern: str | None = None
    schedule_time: str | None = None
    default_segment_id: int | None = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    pillar: str | None
    platform_instructions: dict[str, str]
    raw_text_template: str | None
    variables: list[TemplateVariable]
    schedule_pattern: str | None
    schedule_time: str | None
    default_segment_id: int | None
    created_at: datetime
    updated_at: datetime | None


class GenerateFromTemplateRequest(BaseModel):
    variable_values: dict[str, str] = Field(default_factory=dict)
    platforms: list[str]
    scheduled_date: str
    scheduled_time: str | None = None


class BatchGenerateRequest(BaseModel):
    variable_values: dict[str, str]
    platforms: list[str]
    weeks: int = 4
    scheduled_time: str | None = None


class BatchGenerateResponse(BaseModel):
    created: int
    drafts: list[ContentRowResponse]


# --- Media Browse/Search ---


class MediaTagResponse(BaseModel):
    id: int
    tag: str
    confidence: float
    source: str


class MediaItemResponse(BaseModel):
    id: int
    filename: str
    local_path: str
    thumbnail_path: str | None = None
    mime_type: str
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    pillar: str | None = None
    source: str
    usage_count: int = 0
    avg_engagement: float = 0.0
    created_at: datetime
    alt_text: str | None = None
    default_caption: str | None = None
    season: str | None = None
    original_url: str | None = None


class MediaBrowseResponse(BaseModel):
    items: list[MediaItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    storage_used_bytes: int = 0


MEDIA_SEASONS = frozenset({"spring", "summer", "fall", "winter", "any"})


class MediaUpdateRequest(BaseModel):
    """PATCH body for media metadata.

    All fields optional; a field present with null CLEARS it; absent fields
    are untouched (distinguished via model_fields_set).
    """

    alt_text: str | None = None
    default_caption: str | None = None
    season: str | None = None
    pillar: str | None = None

    @field_validator("season")
    @classmethod
    def _validate_season(cls, v: str | None) -> str | None:
        if v is None:
            return v
        lowered = v.lower()
        if lowered not in MEDIA_SEASONS:
            raise ValueError("season must be one of: spring, summer, fall, winter, any")
        return lowered


class MediaUsageResponse(BaseModel):
    content_row_id: int
    date: datetime | None = None
    status: str
    pillar: str | None = None


class MediaPerformanceResponse(BaseModel):
    id: int
    platform: str
    engagement_score: float
    content_row_id: int | None = None
    fetched_at: datetime


class MediaDetailResponse(BaseModel):
    media: MediaItemResponse
    tags: list[MediaTagResponse]
    usage: list[MediaUsageResponse]
    performance: list[MediaPerformanceResponse]


class MediaTagUpdateRequest(BaseModel):
    add: list[str] = []
    remove: list[str] = []


class MediaDeleteResponse(BaseModel):
    deleted: bool
    id: int


# --- Iteration ---


class IterateRequest(BaseModel):
    content_row_id: int
    platform: str
    instruction: str = Field(max_length=2000)
    mode: str = "refine"


class IterateResponse(BaseModel):
    caption: str
    iteration_id: int


class IterationResponse(BaseModel):
    id: int
    content_row_id: int
    platform: str
    old_caption: str | None
    new_caption: str
    refinement_instruction: str | None
    mode: str
    model_used: str | None = None
    created_by: int | None
    created_at: datetime
