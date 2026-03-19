"""WordPress REST API crawler for gitavalley.com."""

import hashlib
import json
import logging
import re
import sqlite3
import subprocess
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

VALID_FACT_TYPES = {"program", "event", "quote", "link", "description"}


def _call_claude(prompt: str) -> str:
    """Call Claude CLI and return the raw text response."""
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout.strip()


class WordPressCrawler:
    """Fetches pages and posts from a WordPress site via its public REST API."""

    def __init__(
        self,
        base_url: str = "https://gitavalley.org",
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

    # ------------------------------------------------------------------
    # AI classification and extraction
    # ------------------------------------------------------------------

    def classify_pillar(self, title: str, body_text: str, pillars: list[str]) -> str:
        """Use Claude CLI to classify a page into one of the known pillars."""
        pillar_list = ", ".join(pillars)
        prompt = (
            f"Classify this web page into exactly one of these categories: {pillar_list}\n\n"
            f"Title: {title}\n"
            f"Content (first 500 chars): {body_text[:500]}\n\n"
            f"Reply with ONLY the category name, nothing else."
        )
        raw = _call_claude(prompt).strip()
        if raw in pillars:
            return raw
        logger.warning("Unrecognised pillar %r, using first pillar", raw)
        return pillars[0] if pillars else "General"

    def extract_knowledge(self, title: str, body_text: str) -> list[dict]:
        """Use Claude CLI to extract structured facts from page content."""
        prompt = (
            "Extract key facts from this web page as a JSON array. "
            "Each item must have: fact_type (one of: program, event, quote, link, description), "
            "content (the fact text), keywords (list of strings).\n\n"
            f"Title: {title}\n"
            f"Content (first 1000 chars): {body_text[:1000]}\n\n"
            "Reply with ONLY valid JSON, no markdown fences."
        )
        raw = _call_claude(prompt)
        try:
            facts = json.loads(raw)
            if not isinstance(facts, list):
                return []
            # Validate fact_types
            return [
                f
                for f in facts
                if isinstance(f, dict)
                and f.get("fact_type") in VALID_FACT_TYPES
                and f.get("content")
            ]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse knowledge extraction response")
            return []

    # ------------------------------------------------------------------
    # Database storage (sync, uses sqlite3 directly)
    # ------------------------------------------------------------------

    def store_page_sync(self, db_path: str, page_data: dict, pillar: str | None = None) -> int:
        """Insert or update a web page row. Returns the page id."""
        conn = sqlite3.connect(db_path)
        now = datetime.now(timezone.utc).isoformat()

        existing = conn.execute(
            "SELECT id FROM web_pages WHERE url = ? AND site = ?",
            (page_data["url"], page_data["site"]),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE web_pages
                   SET title = ?, body_text = ?, pillar = ?, content_hash = ?, last_crawled = ?
                   WHERE id = ?""",
                (
                    page_data["title"],
                    page_data["body_text"],
                    pillar,
                    page_data["content_hash"],
                    now,
                    existing[0],
                ),
            )
            conn.commit()
            page_id = existing[0]
        else:
            cursor = conn.execute(
                """INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    page_data["url"],
                    page_data["site"],
                    page_data["title"],
                    page_data["body_text"],
                    pillar,
                    page_data["content_hash"],
                    now,
                    now,
                ),
            )
            conn.commit()
            page_id = cursor.lastrowid

        conn.close()
        return page_id

    def store_knowledge_sync(
        self, db_path: str, page_id: int, knowledge: list[dict], pillar: str | None = None
    ) -> None:
        """Store extracted knowledge entries for a page."""
        conn = sqlite3.connect(db_path)
        for fact in knowledge:
            conn.execute(
                """INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    page_id,
                    fact["fact_type"],
                    fact["content"],
                    pillar,
                    json.dumps(fact.get("keywords", [])),
                ),
            )
        conn.commit()
        conn.close()

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
