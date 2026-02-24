"""Postiz API client for scheduling and publishing.

API docs: /api/docs (Swagger) on the Postiz instance.
Auth: Authorization header with API key (no Bearer prefix).
Rate limit: 30 requests/hour.
"""

import logging
import time
from datetime import datetime

import requests

from content_engine.models import ContentPillar, Platform, PostPerformance

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds

# Map Postiz provider identifiers to our Platform enum
_PROVIDER_TO_PLATFORM = {
    "instagram": Platform.INSTAGRAM,
    "facebook": Platform.FACEBOOK,
    "tiktok": Platform.TIKTOK,
    "threads": Platform.THREADS,
    "linkedin": Platform.LINKEDIN,
}


class PostizAPIError(Exception):
    """Raised when the Postiz API returns an unrecoverable error."""


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

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """Make API request with retry on rate limit (429)."""
        for attempt in range(MAX_RETRIES):
            resp = self.session.request(method, f"{self.base_url}{path}", **kwargs)

            if resp.status_code == 429:
                if attempt == MAX_RETRIES - 1:
                    raise PostizAPIError(f"Rate limit exceeded after {MAX_RETRIES} attempts")
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d). Retrying in %.1fs",
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

    def upload_media(self, url: str) -> str:
        """Download media from URL and upload to Postiz.

        Returns the Postiz media ID.
        """
        # Download the file
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        filename = url.split("/")[-1] or "media"

        # Upload to Postiz
        result = self._request(
            "POST",
            "/media",
            files={"file": (filename, resp.content, content_type)},
        )
        return result["id"]

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
