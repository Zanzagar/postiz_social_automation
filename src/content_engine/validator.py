"""Content validation — verify rows are ready for AI generation."""

import logging

import requests

from content_engine.models import ContentRow

logger = logging.getLogger(__name__)

SUPPORTED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "image/gif",
}


class ContentValidator:
    """Validates content rows before AI generation."""

    def validate_row(self, row: ContentRow) -> tuple[bool, str | None]:
        """Validate a content row is ready for AI generation.

        Returns (is_valid, error_message).
        """
        if not row.raw_text or not row.raw_text.strip():
            return False, "Missing raw_text caption"

        if not row.platforms or not any(row.platforms.values()):
            return False, "No platforms selected"

        if row.media_url:
            if not self._is_media_accessible(str(row.media_url)):
                return False, f"Media URL not accessible: {row.media_url}"

        return True, None

    def validate_media_format(self, url: str) -> tuple[bool, str | None]:
        """Validate media is a supported format (JPEG, PNG, WebP, MP4, GIF)."""
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                return False, f"Media URL returned status {resp.status_code}"

            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
            if content_type not in SUPPORTED_MEDIA_TYPES:
                return False, f"Unsupported media format: {content_type}"

            return True, None
        except requests.RequestException as e:
            return False, f"Media URL check failed: {e}"

    def _is_media_accessible(self, url: str) -> bool:
        """Check if media URL returns 200 via HEAD request."""
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            return resp.status_code == 200
        except requests.RequestException:
            return False
