"""Meta Graph API importer for Facebook and Instagram social history."""

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_HASHTAG_RE = re.compile(r"#(\w+)")


class MetaGraphImporter:
    """Imports post history from Facebook and Instagram via Meta Graph API."""

    def __init__(
        self,
        access_token: str,
        page_id: str | None = None,
        instagram_account_id: str | None = None,
        api_version: str = "v19.0",
    ):
        self.access_token = access_token
        self.page_id = page_id
        self.instagram_account_id = instagram_account_id
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def extract_hashtags(text: str | None) -> list[str]:
        """Parse hashtags from post text."""
        if not text:
            return []
        return _HASHTAG_RE.findall(text)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_facebook_post(self, post: dict) -> dict:
        """Convert a Graph API Facebook post into a storage-ready dict."""
        message = post.get("message", "")
        media_urls = []
        attachments = post.get("attachments", {}).get("data", [])
        for att in attachments:
            media = att.get("media", {})
            image = media.get("image", {})
            if image.get("src"):
                media_urls.append(image["src"])

        return {
            "platform": "facebook",
            "external_id": post["id"],
            "post_text": message,
            "media_urls": media_urls,
            "hashtags": self.extract_hashtags(message),
            "posted_at": post.get("created_time", ""),
            "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares": post.get("shares", {}).get("count", 0),
            "reach": 0,
        }

    def parse_instagram_post(self, post: dict) -> dict:
        """Convert a Graph API Instagram media into a storage-ready dict."""
        caption = post.get("caption", "")
        media_url = post.get("media_url", "")
        return {
            "platform": "instagram",
            "external_id": post["id"],
            "post_text": caption,
            "media_urls": [media_url] if media_url else [],
            "hashtags": self.extract_hashtags(caption),
            "posted_at": post.get("timestamp", ""),
            "likes": post.get("like_count", 0),
            "comments": post.get("comments_count", 0),
            "shares": 0,
            "reach": 0,
        }

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    async def fetch_facebook_posts(self) -> list[dict]:
        """Fetch all posts from the configured Facebook page."""
        if not self.page_id:
            logger.warning("No page_id configured, skipping Facebook")
            return []

        url = f"{self.base_url}/{self.page_id}/posts"
        params = {
            "fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true)",
            "access_token": self.access_token,
            "limit": 25,
        }

        all_posts: list[dict] = []
        while url:
            resp = await self._client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Facebook API returned %d: %s", resp.status_code, resp.text[:200])
                break

            data = resp.json()
            for post in data.get("data", []):
                all_posts.append(self.parse_facebook_post(post))

            # Pagination
            next_url = data.get("paging", {}).get("next")
            if next_url:
                url = next_url
                params = {}  # next URL includes all params
            else:
                break

        logger.info("Fetched %d Facebook posts", len(all_posts))
        return all_posts

    async def fetch_instagram_posts(self) -> list[dict]:
        """Fetch all posts from the configured Instagram account."""
        if not self.instagram_account_id:
            logger.debug("No instagram_account_id configured, skipping Instagram")
            return []

        url = f"{self.base_url}/{self.instagram_account_id}/media"
        params = {
            "fields": "id,caption,timestamp,media_url,like_count,comments_count",
            "access_token": self.access_token,
            "limit": 100,
        }

        all_posts: list[dict] = []
        while url:
            resp = await self._client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Instagram API returned %d", resp.status_code)
                break

            data = resp.json()
            for post in data.get("data", []):
                all_posts.append(self.parse_instagram_post(post))

            next_url = data.get("paging", {}).get("next")
            if next_url:
                url = next_url
                params = {}
            else:
                break

        logger.info("Fetched %d Instagram posts", len(all_posts))
        return all_posts

    async def import_all(self) -> list[dict]:
        """Import posts from all configured platforms."""
        posts = []
        posts.extend(await self.fetch_facebook_posts())
        posts.extend(await self.fetch_instagram_posts())
        return posts

    # ------------------------------------------------------------------
    # Database storage (sync, sqlite3)
    # ------------------------------------------------------------------

    def store_post_sync(self, db_path: str, post: dict) -> None:
        """Insert a social history post, skipping duplicates."""
        conn = sqlite3.connect(db_path)
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO social_history
                   (platform, external_id, post_text, media_urls, hashtags,
                    posted_at, likes, comments, shares, reach, pillar, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    post["platform"],
                    post["external_id"],
                    post["post_text"],
                    json.dumps(post.get("media_urls", [])),
                    json.dumps(post.get("hashtags", [])),
                    post.get("posted_at", ""),
                    post.get("likes", 0),
                    post.get("comments", 0),
                    post.get("shares", 0),
                    post.get("reach", 0),
                    post.get("pillar"),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
