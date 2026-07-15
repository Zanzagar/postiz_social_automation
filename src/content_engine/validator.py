"""Content validation — verify rows are ready for AI generation."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests

from content_engine.models import ContentRow

logger = logging.getLogger(__name__)

# NOTE: image/gif is intentionally excluded — Postiz upload (the hard gate in
# content_engine.postiz) rejects GIF, so we reject it up front to fail early.
SUPPORTED_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
}

# Allowed URL schemes for media downloads
_ALLOWED_SCHEMES = {"http", "https"}


def validate_external_url(url: str) -> None:
    """Validate that a URL points to an external (non-private) host.

    Raises ValueError if the URL targets a private/internal IP, localhost,
    or uses a non-HTTP scheme. Prevents SSRF attacks.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed (must be http or https)")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname '{hostname}'") from exc

    for _, _, _, _, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("URL resolves to non-public IP address")


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
        """Validate media is a supported format (JPEG, PNG, WebP, MP4)."""
        try:
            validate_external_url(url)
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                return False, f"Media URL returned status {resp.status_code}"

            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
            if content_type == "image/gif":
                return False, (
                    "GIF is not supported for publishing (rejected at Postiz upload). "
                    "Convert animated GIFs to MP4, or static GIFs to JPEG/PNG."
                )
            if content_type not in SUPPORTED_MEDIA_TYPES:
                return False, f"Unsupported media format: {content_type}"

            return True, None
        except requests.RequestException as e:
            return False, f"Media URL check failed: {e}"

    def _is_media_accessible(self, url: str) -> bool:
        """Check if media URL returns 200 via HEAD request."""
        try:
            validate_external_url(url)
            resp = requests.head(url, timeout=10, allow_redirects=True)
            return resp.status_code == 200
        except (requests.RequestException, ValueError):
            return False
