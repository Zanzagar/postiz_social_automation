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
        ["claude", "-p", prompt, "--bare"],
        capture_output=True,
        text=True,
        timeout=300,
        stdin=subprocess.DEVNULL,
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

    # Content types to crawl from the WordPress REST API
    CONTENT_TYPES = ["posts", "pages", "product"]

    async def crawl_all(self) -> list[dict]:
        """Crawl posts, pages, and products — return parsed page dicts."""
        results = []
        counts = {}
        for content_type in self.CONTENT_TYPES:
            raw = await self.fetch_all_items(content_type)
            counts[content_type] = len(raw)
            for item in raw:
                results.append(self.parse_wp_item(item))

        parts = ", ".join(f"{v} {k}" for k, v in counts.items() if v > 0)
        logger.info("Crawled %d items from %s (%s)", len(results), self.base_url, parts)
        return results

    # ------------------------------------------------------------------
    # AI classification and extraction
    # ------------------------------------------------------------------

    # Pages too short or clearly non-content
    MIN_CONTENT_LENGTH = 200

    # Max chars per chunk sent to Claude
    CHUNK_SIZE = 6000

    # Max chars for pillar classification (just needs enough to understand the topic)
    MAX_CLASSIFY_CHARS = 2000

    @staticmethod
    def _chunk_text(text: str, chunk_size: int) -> list[str]:
        """Split text into chunks, breaking at paragraph boundaries when possible."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        remaining = text
        while remaining:
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break

            # Try to break at a paragraph boundary
            cut = remaining[:chunk_size].rfind("\n\n")
            if cut < chunk_size // 2:
                # No good paragraph break — try sentence boundary
                cut = remaining[:chunk_size].rfind(". ")
                if cut < chunk_size // 2:
                    cut = chunk_size  # Hard cut
                else:
                    cut += 1  # Include the period

            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()

        return chunks

    def classify_pillar(self, title: str, body_text: str, pillars: list[str]) -> str:
        """Use Claude CLI to classify a page into one of the known pillars."""
        pillar_list = ", ".join(pillars)
        content = body_text[: self.MAX_CLASSIFY_CHARS]
        prompt = (
            f"Classify this web page into exactly one of these categories: {pillar_list}\n\n"
            f"Title: {title}\n"
            f"Content:\n{content}\n\n"
            f"Reply with ONLY the category name, nothing else."
        )
        raw = _call_claude(prompt).strip()
        if raw in pillars:
            return raw
        logger.warning("Unrecognised pillar %r, using first pillar", raw)
        return pillars[0] if pillars else "General"

    def _extract_chunk(
        self, title: str, chunk: str, chunk_num: int, total_chunks: int
    ) -> list[dict]:
        """Extract knowledge from a single chunk of text."""
        context = f" (chunk {chunk_num}/{total_chunks})" if total_chunks > 1 else ""
        topics = (
            "Cow Protection, Ahimsa Dairy, Farm Products, Sustainability, "
            "Retreats & Visits, People & Team, Education & Programs, "
            "History & Mission, Fundraising, General Information"
        )
        prompt = (
            "Extract key facts from this web page content as a JSON array. "
            "Each item must have:\n"
            "- fact_type (one of: program, event, quote, link, description)\n"
            "- content (the fact text — be specific with names, numbers, dates)\n"
            "- topic (one of: " + topics + ")\n"
            "- keywords (list of strings)\n\n"
            "Focus on: programs offered, events, notable quotes, specific facts about "
            "the farm/community, and descriptions of activities or initiatives.\n"
            "Skip generic marketing language and boilerplate.\n\n"
            f"Title: {title}{context}\n"
            f"Content:\n{chunk}\n\n"
            "Reply with ONLY valid JSON, no markdown fences."
        )
        raw = _call_claude(prompt)
        # Strip markdown code fences if present
        text = raw.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if fence_match:
            text = fence_match.group(1).strip()
        try:
            facts = json.loads(text)
            if not isinstance(facts, list):
                return []
            return [
                f
                for f in facts
                if isinstance(f, dict)
                and f.get("fact_type") in VALID_FACT_TYPES
                and f.get("content")
            ]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse extraction response for chunk %d", chunk_num)
            return []

    def extract_knowledge(self, title: str, body_text: str) -> list[dict]:
        """Extract structured facts from page content, chunking large pages."""
        if len(body_text) < self.MIN_CONTENT_LENGTH:
            return []

        chunks = self._chunk_text(body_text, self.CHUNK_SIZE)
        all_facts: list[dict] = []

        for i, chunk in enumerate(chunks, 1):
            facts = self._extract_chunk(title, chunk, i, len(chunks))
            all_facts.extend(facts)

        if len(chunks) > 1:
            logger.info(
                "Extracted %d facts from %d chunks of '%s'",
                len(all_facts),
                len(chunks),
                title[:40],
            )

        # Deduplicate facts with identical content
        seen_content: set[str] = set()
        unique_facts = []
        for f in all_facts:
            key = f["content"].strip().lower()
            if key not in seen_content:
                seen_content.add(key)
                unique_facts.append(f)

        return unique_facts

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
        now = datetime.now(timezone.utc).isoformat()
        for fact in knowledge:
            conn.execute(
                """INSERT INTO web_knowledge (web_page_id, fact_type, content, topic, pillar, keywords, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    page_id,
                    fact["fact_type"],
                    fact["content"],
                    fact.get("topic"),
                    pillar,
                    json.dumps(fact.get("keywords", [])),
                    now,
                ),
            )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Post-extraction topic classification
    # ------------------------------------------------------------------

    KNOWN_TOPICS = [
        "Cow Protection",
        "Ahimsa Dairy",
        "Farm Products",
        "Sustainability",
        "Retreats & Visits",
        "People & Team",
        "Education & Programs",
        "History & Mission",
        "Fundraising",
        "Spiritual Life",
        "Events & Festivals",
        "General Information",
    ]

    def classify_topic(self, fact_content: str) -> str:
        """Classify a single fact into a topic using a focused Claude call."""
        topic_list = ", ".join(self.KNOWN_TOPICS)
        prompt = (
            f"Classify this fact into exactly one topic: {topic_list}\n\n"
            f"Fact: {fact_content[:500]}\n\n"
            f"Reply with ONLY the topic name, nothing else."
        )
        raw = _call_claude(prompt).strip()
        if raw in self.KNOWN_TOPICS:
            return raw
        # Fuzzy match — Claude sometimes adds/drops words
        raw_lower = raw.lower()
        for topic in self.KNOWN_TOPICS:
            if topic.lower() in raw_lower or raw_lower in topic.lower():
                return topic
        logger.warning("Could not classify topic %r, using General Information", raw)
        return "General Information"

    def classify_unclassified_sync(self, db_path: str) -> int:
        """Find all knowledge entries with NULL topic and classify them.

        Returns the number of entries classified.
        """
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, content FROM web_knowledge WHERE topic IS NULL").fetchall()

        if not rows:
            conn.close()
            return 0

        logger.info("Classifying %d unclassified knowledge entries", len(rows))
        classified = 0
        for row in rows:
            try:
                topic = self.classify_topic(row["content"])
                conn.execute(
                    "UPDATE web_knowledge SET topic = ? WHERE id = ?",
                    (topic, row["id"]),
                )
                classified += 1
            except Exception:
                logger.warning("Failed to classify entry %d", row["id"])

        conn.commit()
        conn.close()
        logger.info("Classified %d/%d entries", classified, len(rows))
        return classified

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
