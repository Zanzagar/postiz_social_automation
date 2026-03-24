"""Import media from social_history posts via Meta Graph API.

Fetches post attachments, downloads images, and catalogs them
with AI tagging and engagement data from the original post.

Usage:
    python -m content_engine.scripts.import_social_media
"""

import json
import logging
import os
import uuid
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Import models — use absolute path resolution for DB
MEDIA_DIR = Path("media")
THUMBNAIL_SIZE = (200, 200)


def get_engine():
    db_path = os.environ.get("DATABASE_PATH", "data/gvsa.db")
    return create_engine(f"sqlite:///{db_path}")


def fetch_post_attachments(post_id: str, access_token: str) -> list[str]:
    """Fetch media attachment URLs for a Facebook post via Graph API."""
    url = f"https://graph.facebook.com/v21.0/{post_id}"
    params = {
        "fields": "attachments{media,subattachments}",
        "access_token": access_token,
    }
    try:
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Failed to fetch attachments for %s: %s", post_id, e)
        return []

    image_urls = []
    attachments = data.get("attachments", {}).get("data", [])
    for att in attachments:
        media = att.get("media", {})
        if "image" in media:
            src = media["image"].get("src")
            if src:
                image_urls.append(src)
        # Check subattachments (carousel posts)
        for sub in att.get("subattachments", {}).get("data", []):
            sub_media = sub.get("media", {})
            if "image" in sub_media:
                src = sub_media["image"].get("src")
                if src:
                    image_urls.append(src)

    return image_urls


def download_image(url: str) -> bytes | None:
    """Download image content from URL."""
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            return None
        return resp.content
    except Exception as e:
        logger.warning("Download failed: %s — %s", url, e)
        return None


def _classify_media_tags(image_path: str) -> list[dict]:
    """Wrapper that lazy-imports from api.routes.media."""
    from api.routes.media import _classify_media_tags as _impl

    return _impl(image_path)


def main():
    # Lazy import to avoid circular deps at module level
    from api.models import MediaCatalog, MediaPerformance, MediaTag, SocialHistory

    access_token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not access_token:
        logger.error("META_PAGE_ACCESS_TOKEN env var required")
        return

    engine = get_engine()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "thumbnails").mkdir(exist_ok=True)

    with Session(engine) as session:
        # Get all social history posts
        posts = (
            session.execute(select(SocialHistory).where(SocialHistory.platform == "facebook"))
            .scalars()
            .all()
        )
        logger.info("Found %d Facebook posts in social_history", len(posts))

        # Get already-imported social media IDs
        existing = (
            session.execute(
                select(MediaCatalog.original_url).where(MediaCatalog.source == "social_import")
            )
            .scalars()
            .all()
        )
        existing_urls = set(existing)

        imported = 0
        skipped = 0

        for post in posts:
            social_url = f"social_history:{post.id}"
            if social_url in existing_urls:
                skipped += 1
                continue

            # Fetch attachment URLs from Graph API
            image_urls = fetch_post_attachments(post.external_id, access_token)
            if not image_urls:
                continue

            for img_url in image_urls:
                content = download_image(img_url)
                if not content:
                    continue

                # Save locally
                stored_name = f"{uuid.uuid4().hex}.jpg"
                file_path = MEDIA_DIR / stored_name
                file_path.write_bytes(content)

                # Dimensions
                width = height = None
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                except Exception:
                    pass

                # Thumbnail
                thumb_path = MEDIA_DIR / "thumbnails" / f"thumb_{stored_name}"
                try:
                    with Image.open(file_path) as img:
                        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                        img.save(thumb_path)
                except Exception:
                    thumb_path = None

                # AI tagging
                tag_results = _classify_media_tags(str(file_path))

                # Determine pillar from post
                pillar = post.pillar

                # Create catalog entry
                catalog = MediaCatalog(
                    filename=f"{post.platform}_{post.external_id}.jpg",
                    original_url=social_url,
                    local_path=str(file_path),
                    thumbnail_path=str(thumb_path) if thumb_path else None,
                    mime_type="image/jpeg",
                    width=width,
                    height=height,
                    file_size=len(content),
                    tags=json.dumps([t["tag"] for t in tag_results]) if tag_results else None,
                    pillar=pillar,
                    source="social_import",
                    avg_engagement=float(post.likes + post.comments + post.shares),
                )
                session.add(catalog)
                session.flush()

                # Tags
                for t in tag_results:
                    session.add(
                        MediaTag(
                            media_id=catalog.id,
                            tag=t["tag"],
                            confidence=t.get("confidence", 0.5),
                            source="ai",
                        )
                    )

                # Performance record from social history data
                session.add(
                    MediaPerformance(
                        media_id=catalog.id,
                        content_row_id=None,
                        platform=post.platform,
                        engagement_score=float(post.likes + post.comments * 2 + post.shares * 3),
                    )
                )

                imported += 1
                if imported % 10 == 0:
                    session.commit()
                    logger.info("Imported %d media so far...", imported)

        session.commit()

    logger.info("Done. Imported: %d, Skipped (already exists): %d", imported, skipped)


if __name__ == "__main__":
    main()
