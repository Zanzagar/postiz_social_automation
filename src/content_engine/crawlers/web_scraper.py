"""BeautifulSoup web scraper for iskcongitanagari.org."""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraper:
    """BFS web scraper with robots.txt compliance and rate limiting."""

    def __init__(
        self,
        base_url: str,
        site_name: str,
        rate_limit: float = 1.0,
        max_pages: int = 200,
    ):
        self.base_url = base_url.rstrip("/")
        self.site_name = site_name
        self.rate_limit = rate_limit
        self.max_pages = max_pages
        self._robot_parser = RobotFileParser()
        self._last_request: float = 0

    # ------------------------------------------------------------------
    # Robots.txt
    # ------------------------------------------------------------------

    def parse_robots(self, robots_text: str) -> None:
        """Parse a robots.txt string."""
        self._robot_parser.parse(robots_text.splitlines())

    def can_fetch(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        return self._robot_parser.can_fetch("*", url)

    # ------------------------------------------------------------------
    # Content extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_content(html: str) -> dict:
        """Extract title and body text from HTML, stripping non-content elements."""
        if not html:
            return {"title": "", "body_text": ""}

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else ""

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        body_text = soup.get_text(separator=" ", strip=True)
        return {"title": title or "", "body_text": body_text}

    def discover_links(self, html: str, current_url: str) -> list[str]:
        """Find all internal links in HTML, return absolute URLs."""
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(self.base_url).netloc
        seen = set()
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute = urljoin(current_url, href)
            # Strip fragment
            absolute = absolute.split("#")[0]
            parsed = urlparse(absolute)
            if parsed.netloc != base_domain:
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            links.append(absolute)

        return links

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """SHA-256 hash for change detection."""
        return hashlib.sha256(text.encode()).hexdigest()

    # ------------------------------------------------------------------
    # HTTP fetching
    # ------------------------------------------------------------------

    async def fetch_page(self, url: str) -> str | None:
        """Fetch a page with rate limiting. Returns HTML or None."""
        if not self.can_fetch(url):
            logger.debug("Blocked by robots.txt: %s", url)
            return None

        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            import asyncio

            await asyncio.sleep(self.rate_limit - elapsed)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, follow_redirects=True)
            self._last_request = time.time()
            if resp.status_code != 200:
                logger.warning("HTTP %d for %s", resp.status_code, url)
                return None
            return resp.text

    # ------------------------------------------------------------------
    # BFS crawl
    # ------------------------------------------------------------------

    async def crawl_site(self) -> list[dict]:
        """BFS crawl starting from base_url. Returns list of page dicts."""
        visited: set[str] = set()
        queue = [self.base_url + "/"]
        results = []

        while queue and len(visited) < self.max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            html = await self.fetch_page(url)
            if html is None:
                continue

            content = self.extract_content(html)
            body_text = content["body_text"]
            page_data = {
                "url": url,
                "title": content["title"],
                "body_text": body_text,
                "content_hash": self.compute_content_hash(body_text),
                "site": self.site_name,
            }
            results.append(page_data)

            # Discover and enqueue new links
            new_links = self.discover_links(html, url)
            for link in new_links:
                if link not in visited:
                    queue.append(link)

        logger.info("Crawled %d pages from %s", len(results), self.base_url)
        return results

    # ------------------------------------------------------------------
    # Database storage (sync, sqlite3)
    # ------------------------------------------------------------------

    def store_page_sync(self, db_path: str, page_data: dict, pillar: str | None = None) -> int:
        """Insert or update a web page. Returns page id."""
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
