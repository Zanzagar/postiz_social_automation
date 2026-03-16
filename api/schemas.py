"""Pydantic response/request schemas for the API."""

from datetime import datetime

from pydantic import BaseModel

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
    raw_text: str
    media_url: str | None = None
    platforms: list[str]
    scheduled_date: str


class RepromptRequest(BaseModel):
    raw_text: str
    media_url: str | None = None
    platforms: list[str]
    scheduled_date: str
    feedback: str


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
