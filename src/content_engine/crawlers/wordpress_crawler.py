"""WordPress REST API crawler for gitavalley.com."""

import hashlib
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class WordPressCrawler:
    """Fetches pages and posts from a WordPress site via its public REST API."""

    def __init__(
        self,
        base_url: str = "https://gitavalley.com",
        site_name: str = "gitavalley",
        per_page: int = 100,
    ):
        self.base_url = base_url.rstrip("/")
        self.site_name = site_name
        self.per_page = per_page
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def strip_html(html: str) -> str:
        """Remove HTML tags and collapse whitespace."""
        if not html:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
        text = _TAG_RE.sub(" ", text)
        text = _WS_RE.sub(" ", text).strip()
        return text

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """SHA-256 hash of body text for change detection."""
        return hashlib.sha256(text.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_wp_item(self, item: dict) -> dict:
        """Convert a WP REST API post/page JSON into a flat dict for storage."""
        body_text = self.strip_html(item.get("content", {}).get("rendered", ""))
        return {
            "url": item.get("link", ""),
            "title": self.strip_html(item.get("title", {}).get("rendered", "")),
            "body_text": body_text,
            "content_hash": self.compute_content_hash(body_text),
            "site": self.site_name,
        }

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    async def fetch_all_items(self, endpoint: str) -> list[dict]:
        """Fetch all items from a WP REST endpoint with pagination.

        Args:
            endpoint: "posts" or "pages".
        """
        url = f"{self.base_url}/wp-json/wp/v2/{endpoint}"
        all_items: list[dict] = []
        page = 1

        while True:
            resp = await self._client.get(url, params={"per_page": self.per_page, "page": page})
            if resp.status_code != 200:
                logger.warning("WP API %s returned %d", endpoint, resp.status_code)
                break

            items = resp.json()
            if not items:
                break

            all_items.extend(items)

            total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
            if page >= total_pages:
                break
            page += 1

        return all_items

    # ------------------------------------------------------------------
    # High-level
    # ------------------------------------------------------------------

    async def crawl_all(self) -> list[dict]:
        """Crawl both posts and pages, return parsed page dicts."""
        raw_posts = await self.fetch_all_items("posts")
        raw_pages = await self.fetch_all_items("pages")

        results = []
        for item in raw_posts + raw_pages:
            results.append(self.parse_wp_item(item))

        logger.info(
            "Crawled %d items from %s (%d posts, %d pages)",
            len(results),
            self.base_url,
            len(raw_posts),
            len(raw_pages),
        )
        return results

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
