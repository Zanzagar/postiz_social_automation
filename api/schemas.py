"""Pydantic response/request schemas for the API."""

from datetime import datetime

from pydantic import BaseModel, Field

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


class SuggestionResponse(BaseModel):
    """JSON-serializable suggestion."""

    suggested_date: datetime
    content_idea: str
    suggested_pillar: str
    rationale: str
    media_suggestion: str
    status: str = "suggested"


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


class EditCaptionsRequest(BaseModel):
    captions: dict[str, str]
    platforms: dict[str, bool] | None = None


# --- Pillars ---


class PillarResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    color: str | None = None
    is_active: bool = True
    sort_order: int = 0
    target_distribution: float | None = None


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
    created_by: int | None
    created_at: datetime
