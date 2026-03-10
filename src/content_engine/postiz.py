"""Postiz API client for scheduling and publishing.

API docs: /api/docs (Swagger) on the Postiz instance.
Auth: Authorization header with API key (no Bearer prefix).
Rate limit: 30 requests/hour.
"""

import logging
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from content_engine.models import ContentPillar, Platform, PostPerformance

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_VIDEO_TYPES = {"video/mp4"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB

# Map Postiz provider identifiers to our Platform enum
_PROVIDER_TO_PLATFORM = {
    "instagram": Platform.INSTAGRAM,
    "facebook": Platform.FACEBOOK,
    "tiktok": Platform.TIKTOK,
    "threads": Platform.THREADS,
    "linkedin": Platform.LINKEDIN,
}


def parse_google_drive_url(url: str) -> str:
    """Convert Google Drive sharing URL to direct download URL.

    Supports:
    - https://drive.google.com/file/d/{ID}/view?...
    - https://drive.google.com/open?id={ID}
    - https://drive.google.com/uc?export=download&id={ID} (passthrough)

    Non-Google-Drive URLs are returned unchanged.
    """
    parsed = urlparse(url)
    if "drive.google.com" not in parsed.netloc:
        return url

    # Already a direct download URL
    if parsed.path == "/uc" and "id=" in url:
        return url

    # /file/d/{FILE_ID}/view pattern
    match = re.search(r"/file/d/([^/]+)", parsed.path)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # /open?id={FILE_ID} pattern
    qs = parse_qs(parsed.query)
    if "id" in qs:
        file_id = qs["id"][0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    raise ValueError(f"Cannot extract file ID from Google Drive URL: {url}")


class PostizAPIError(Exception):
    """Raised when the Postiz API returns an unrecoverable error."""


class MediaValidationError(Exception):
    """Raised when media fails format, size, or platform validation."""


class PostizClient:
    """Client for the Postiz social media scheduling API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://postiz.sethpc.xyz/api/public/v1",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_key})

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "PostizClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """Make API request with retry on rate limit (429) and transient 5xx errors."""
        for attempt in range(MAX_RETRIES):
            resp = self.session.request(method, f"{self.base_url}{path}", **kwargs)

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    reason = (
                        "Rate limit"
                        if resp.status_code == 429
                        else f"Server error {resp.status_code}"
                    )
                    raise PostizAPIError(f"{reason} after {MAX_RETRIES} attempts")
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "Retryable error %d (attempt %d/%d). Retrying in %.1fs",
                    resp.status_code,
                    attempt + 1,
                    MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        raise PostizAPIError("Unexpected retry loop exit")

    def list_integrations(self) -> list[dict]:
        """Get connected social media channels."""
        return self._request("GET", "/integrations")

    def create_draft_post(
        self,
        content: str,
        platform_ids: list[str],
        media_url: str | None = None,
        scheduled_at: str | None = None,
    ) -> dict:
        """Create a draft post in Postiz.

        Args:
            content: The post caption/text.
            platform_ids: List of Postiz integration IDs to post to.
            media_url: Optional URL to media (will be uploaded).
            scheduled_at: Optional ISO datetime for scheduling.
        """
        payload: dict = {
            "content": content,
            "integrations": platform_ids,
            "status": "draft",
        }
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at
        if media_url:
            media_id = self.upload_media(media_url)
            payload["media"] = [media_id]

        return self._request("POST", "/posts", json=payload)

    def validate_media(self, content_type: str, file_size: int) -> None:
        """Validate media format and size.

        Raises MediaValidationError if validation fails.
        """
        all_supported = SUPPORTED_IMAGE_TYPES | SUPPORTED_VIDEO_TYPES
        if content_type not in all_supported:
            raise MediaValidationError(f"Unsupported media type: {content_type}")

        if content_type in SUPPORTED_IMAGE_TYPES and file_size > MAX_IMAGE_SIZE:
            raise MediaValidationError(f"Image size {file_size} exceeds {MAX_IMAGE_SIZE} limit")
        if content_type in SUPPORTED_VIDEO_TYPES and file_size > MAX_VIDEO_SIZE:
            raise MediaValidationError(f"Video size {file_size} exceeds {MAX_VIDEO_SIZE} limit")

    def upload_media(self, url: str) -> str:
        """Download media from URL, validate, and upload to Postiz.

        Handles Google Drive sharing links automatically.
        Returns the Postiz media ID.
        """
        download_url = parse_google_drive_url(url)

        # Download to temp file
        resp = requests.get(download_url, stream=True, timeout=60)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="postiz_media_", delete=False) as tmp:
                for chunk in resp.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = Path(tmp.name)

            file_size = tmp_path.stat().st_size
            self.validate_media(content_type=content_type, file_size=file_size)

            # Upload to Postiz
            with open(tmp_path, "rb") as f:
                filename = tmp_path.name
                result = self._request(
                    "POST",
                    "/media",
                    files={"file": (filename, f, content_type)},
                )
            return result["id"]
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

    def get_post_analytics(
        self,
        post_id: str,
        pillar: ContentPillar,
    ) -> PostPerformance:
        """Get engagement metrics for a published post."""
        data = self._request("GET", f"/posts/{post_id}")

        provider = data.get("integration", {}).get("providerIdentifier", "")
        platform = _PROVIDER_TO_PLATFORM.get(provider, Platform.INSTAGRAM)

        stats = data.get("statistics", {})
        published_at = data.get("publishedAt", "")

        return PostPerformance(
            post_id=post_id,
            platform=platform,
            pillar=pillar,
            posted_at=datetime.fromisoformat(published_at) if published_at else datetime.now(),
            likes=stats.get("likes", 0),
            comments=stats.get("comments", 0),
            shares=stats.get("shares", 0),
            reach=stats.get("reach", 0),
            engagement_rate=stats.get("engagement_rate", 0.0),
        )
