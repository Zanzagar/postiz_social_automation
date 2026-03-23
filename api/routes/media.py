"""Media catalog endpoints — upload, import, browse."""

import json
import logging
import math
import subprocess
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db, get_settings
from api.models import ContentRow, MediaAdapted, MediaCatalog, MediaPerformance, MediaTag
from api.schemas import (
    MediaBrowseResponse,
    MediaDeleteResponse,
    MediaDetailResponse,
    MediaItemResponse,
    MediaPerformanceResponse,
    MediaTagResponse,
    MediaTagUpdateRequest,
    MediaUsageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media"], dependencies=[Depends(get_current_user)])

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/quicktime",
    "video/webm",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB (videos need more)
THUMBNAIL_SIZE = (400, 400)


def _get_media_dir() -> Path:
    """Return the media storage directory, creating it if needed."""
    media_dir = Path("media")
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "thumbnails").mkdir(exist_ok=True)
    return media_dir


def _generate_thumbnail(src_path: Path, thumb_path: Path) -> None:
    """Generate a 200x200 thumbnail maintaining aspect ratio."""
    with Image.open(src_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        img.save(thumb_path, format="JPEG")


def _upload_to_postiz(file_path: Path) -> str | None:
    """Upload media to Postiz and return the media ID. Returns None on failure."""
    settings = get_settings()
    if not settings.postiz_api_key:
        return None
    try:
        with httpx.Client(timeout=30) as client:
            with open(file_path, "rb") as f:
                resp = client.post(
                    f"{settings.postiz_base_url}/upload",
                    files={"file": (file_path.name, f)},
                    headers={"Authorization": settings.postiz_api_key},
                )
            if resp.status_code == 200:
                return resp.json().get("id")
    except Exception:
        logger.warning("Postiz upload failed for %s", file_path.name, exc_info=True)
    return None


def _classify_media_tags(image_path: str) -> list[dict]:
    """Use Claude CLI to classify image tags. Returns list of {tag, confidence}."""
    prompt = (
        "Analyze this image and classify it with these tags. "
        "Return ONLY a JSON array of objects with 'tag' and 'confidence' (0.0-1.0) fields. "
        "Categories: farm, cows, kitchen, outdoor, people, event, food, landscape, "
        "building, deity, garden, seasonal. "
        "Only include tags with confidence > 0.5."
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text", "--image", image_path],
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
        output = result.stdout.strip()
        if (
            not output
            and isinstance(result, subprocess.CompletedProcess)
            and result.returncode != 0
        ):
            raise RuntimeError(result.stderr[:200])
        # Strip markdown fences if present
        if output.startswith("```"):
            output = output.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(output)
    except subprocess.TimeoutExpired as e:
        stdout = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        if stdout.strip():
            output = stdout.strip()
            if output.startswith("```"):
                output = output.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(output)
        logger.warning("AI tagging timed out for %s", image_path)
    except (json.JSONDecodeError, Exception):
        logger.warning("AI tagging failed for %s", image_path, exc_info=True)
    return []


def _download_from_url(url: str) -> tuple[bytes, str, str]:
    """Download file from URL. Returns (content, mime_type, filename)."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
    content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
    filename = url.rsplit("/", 1)[-1].split("?")[0] or "download.jpg"
    return resp.content, content_type, filename


class MediaUploadResponse(BaseModel):
    id: int
    filename: str
    local_path: str
    thumbnail_path: str | None
    postiz_media_id: str | None
    mime_type: str
    width: int | None
    height: int | None
    file_size: int
    source: str
    original_url: str | None = None
    tags: list[dict] = []


class ImportUrlRequest(BaseModel):
    url: str


async def _process_and_catalog(
    content: bytes,
    filename: str,
    mime_type: str,
    source: str,
    original_url: str | None,
    session: AsyncSession,
) -> MediaUploadResponse:
    """Upload to Drive, cache thumbnail locally, catalog in DB."""
    # Upload to Google Drive
    drive_file_id = None
    subfolder_map = {
        "upload": "Uploads",
        "import_url": "Imports",
        "social_import": "Social Import",
    }
    try:
        from api.routes.drive import upload_to_drive

        result = upload_to_drive(content, filename, mime_type, subfolder_map.get(source, "Uploads"))
        drive_file_id = result["id"]
    except Exception:
        logger.warning(
            "Drive upload failed for %s, storing locally as fallback",
            filename,
            exc_info=True,
        )

    # If Drive upload succeeded, use drive:// reference; else local fallback
    if drive_file_id:
        local_path = f"drive://{drive_file_id}"
        drive_url = f"drive://{drive_file_id}"
    else:
        media_dir = _get_media_dir()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = media_dir / stored_name
        file_path.write_bytes(content)
        local_path = str(file_path)
        drive_url = original_url

    # Image dimensions (from content bytes)
    width = height = None
    if mime_type.startswith("image/"):
        try:
            import io

            with Image.open(io.BytesIO(content)) as img:
                width, height = img.size
        except Exception:
            pass

    # Thumbnail: fetch from Drive if uploaded, else generate locally
    thumb_path = None
    if drive_file_id:
        try:
            from api.routes.drive import _fetch_drive_thumbnail, get_drive_service

            service = get_drive_service()
            thumb_path = _fetch_drive_thumbnail(service, drive_file_id)
        except Exception:
            pass
    if not thumb_path and mime_type.startswith("image/"):
        try:
            media_dir = _get_media_dir()
            stored_name = f"{uuid.uuid4().hex}.jpg"
            tmp_thumb = media_dir / "thumbnails" / f"thumb_{stored_name}"
            import io

            with Image.open(io.BytesIO(content)) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                img.save(tmp_thumb, format="JPEG")
            thumb_path = str(tmp_thumb)
        except Exception:
            pass

    # AI tagging (only for images, needs temp file)
    tag_results = []
    if mime_type.startswith("image/"):
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        tag_results = _classify_media_tags(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

    # DB insert
    catalog = MediaCatalog(
        filename=filename,
        original_url=drive_url,
        local_path=local_path,
        thumbnail_path=thumb_path,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=len(content),
        tags=json.dumps([t["tag"] for t in tag_results]) if tag_results else None,
        source=source,
    )
    session.add(catalog)
    await session.flush()

    for t in tag_results:
        session.add(
            MediaTag(
                media_id=catalog.id,
                tag=t["tag"],
                confidence=t.get("confidence", 0.5),
                source="ai",
            )
        )

    await session.commit()
    await session.refresh(catalog)

    return MediaUploadResponse(
        id=catalog.id,
        filename=catalog.filename,
        local_path=catalog.local_path,
        thumbnail_path=catalog.thumbnail_path,
        postiz_media_id=catalog.postiz_media_id,
        mime_type=catalog.mime_type,
        width=catalog.width,
        height=catalog.height,
        file_size=catalog.file_size,
        source=catalog.source,
        original_url=catalog.original_url,
        tags=[{"tag": t["tag"], "confidence": t.get("confidence", 0.5)} for t in tag_results],
    )


@router.post("/media/upload", response_model=MediaUploadResponse, status_code=201)
async def upload_media(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
):
    """Upload a media file to the catalog with AI tagging."""
    if not file.content_type or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {MAX_FILE_SIZE} bytes.")

    filename = file.filename or "upload.jpg"
    return await _process_and_catalog(content, filename, file.content_type, "upload", None, session)


@router.post("/media/import-url", response_model=MediaUploadResponse, status_code=201)
async def import_media_url(
    req: ImportUrlRequest,
    session: AsyncSession = Depends(get_db),
):
    """Import media from a URL into the catalog."""
    try:
        content, mime_type, filename = _download_from_url(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download: {e}")

    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported type from URL: {mime_type}")

    return await _process_and_catalog(content, filename, mime_type, "import_url", req.url, session)


# ── Browse / Search ─────────────────────────────────────────────────────


@router.get("/media", response_model=MediaBrowseResponse)
async def browse_media(
    tag: str | None = None,
    pillar: str | None = None,
    source: str | None = None,
    sort: str = Query("date", pattern="^(date|engagement|usage_count)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Browse and search the media catalog with pagination and filters."""
    query = select(MediaCatalog)

    if source:
        query = query.where(MediaCatalog.source == source)
    if pillar:
        query = query.where(MediaCatalog.pillar == pillar)
    if tag:
        query = query.join(MediaTag, MediaTag.media_id == MediaCatalog.id).where(
            MediaTag.tag == tag
        )

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Sort
    if sort == "engagement":
        query = query.order_by(MediaCatalog.avg_engagement.desc())
    elif sort == "usage_count":
        query = query.order_by(MediaCatalog.usage_count.desc())
    else:
        query = query.order_by(MediaCatalog.created_at.desc())

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await session.execute(query)
    items = result.scalars().all()

    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 0

    return MediaBrowseResponse(
        items=[
            MediaItemResponse(
                id=m.id,
                filename=m.filename,
                local_path=m.local_path,
                thumbnail_path=m.thumbnail_path,
                mime_type=m.mime_type,
                width=m.width,
                height=m.height,
                file_size=m.file_size,
                pillar=m.pillar,
                source=m.source,
                usage_count=m.usage_count,
                avg_engagement=m.avg_engagement,
                created_at=m.created_at,
            )
            for m in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# ── Suggest ──────────────────────────────────────────────────────────────

# Stop words for keyword extraction
_STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it that this with from by as are "
    "was were be been being have has had do does did will would shall should may "
    "might can could about up out if not no so very just than them their our your "
    "we they he she its his her my me us".split()
)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text for media matching."""
    words = set()
    for word in text.lower().split():
        # Strip punctuation
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned and len(cleaned) > 2 and cleaned not in _STOP_WORDS:
            words.add(cleaned)
    return words


@router.get("/media/suggest")
async def suggest_media(
    content_row_id: int = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Recommend media from catalog based on content row context."""
    # Fetch the content row
    row_result = await session.execute(select(ContentRow).where(ContentRow.id == content_row_id))
    row = row_result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Content row not found")

    # Extract keywords from raw text
    keywords = _extract_keywords(row.raw_text or "")

    # Fetch all media with their tags
    media_result = await session.execute(select(MediaCatalog))
    all_media = media_result.scalars().all()

    if not all_media:
        return {"suggestions": []}

    # Fetch all tags grouped by media_id
    tags_result = await session.execute(select(MediaTag))
    all_tags = tags_result.scalars().all()
    tags_by_media: dict[int, list[str]] = {}
    for t in all_tags:
        tags_by_media.setdefault(t.media_id, []).append(t.tag)

    # Score each media item
    scored = []
    for media in all_media:
        score = 0.0
        reasons: list[str] = []

        # Pillar match (+2)
        if row.pillar and media.pillar and media.pillar == row.pillar:
            score += 2.0
            reasons.append("pillar match")

        # Topic match (+3)
        if media.topic and row.raw_text and media.topic.lower() in row.raw_text.lower():
            score += 3.0
            reasons.append("topic match")

        # Tag matching (+1 per match)
        media_tags = set(tags_by_media.get(media.id, []))
        matching_tags = keywords & media_tags
        score += len(matching_tags)
        for tag in sorted(matching_tags):
            reasons.append(f"tag: {tag}")

        # Engagement score (0-2 range)
        engagement_bonus = min(media.avg_engagement * 2.0, 2.0)
        score += engagement_bonus
        if engagement_bonus > 0.5:
            reasons.append("high engagement")

        # Freshness: prefer less-used media
        if media.usage_count == 0:
            score += 1.0
            reasons.append("unused")
        elif media.usage_count > 5:
            score -= 0.5

        scored.append(
            {
                "media_id": media.id,
                "thumbnail_path": media.thumbnail_path,
                "filename": media.filename,
                "relevance_score": round(score, 2),
                "match_reasons": reasons,
            }
        )

    # Sort by score descending, return top 5
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"suggestions": scored[:5]}


# ── Detail ───────────────────────────────────────────────────────────────


@router.get("/media/{media_id}", response_model=MediaDetailResponse)
async def get_media_detail(
    media_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get detailed media info including tags, usage history, and performance."""
    result = await session.execute(select(MediaCatalog).where(MediaCatalog.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Tags
    tags_result = await session.execute(select(MediaTag).where(MediaTag.media_id == media_id))
    tags = tags_result.scalars().all()

    # Usage: content rows that reference this media ID
    usage_result = await session.execute(select(ContentRow))
    all_rows = usage_result.scalars().all()
    usage = []
    for row in all_rows:
        if row.media_catalog_ids:
            try:
                ids = json.loads(row.media_catalog_ids)
                if media_id in ids:
                    usage.append(
                        MediaUsageResponse(
                            content_row_id=row.id,
                            date=row.date,
                            status=row.status,
                            pillar=row.pillar,
                        )
                    )
            except (json.JSONDecodeError, TypeError):
                pass

    # Performance
    perf_result = await session.execute(
        select(MediaPerformance).where(MediaPerformance.media_id == media_id)
    )
    performance = perf_result.scalars().all()

    return MediaDetailResponse(
        media=MediaItemResponse(
            id=media.id,
            filename=media.filename,
            local_path=media.local_path,
            thumbnail_path=media.thumbnail_path,
            mime_type=media.mime_type,
            width=media.width,
            height=media.height,
            file_size=media.file_size,
            pillar=media.pillar,
            source=media.source,
            usage_count=media.usage_count,
            avg_engagement=media.avg_engagement,
            created_at=media.created_at,
        ),
        tags=[
            MediaTagResponse(id=t.id, tag=t.tag, confidence=t.confidence, source=t.source)
            for t in tags
        ],
        usage=usage,
        performance=[
            MediaPerformanceResponse(
                id=p.id,
                platform=p.platform,
                engagement_score=p.engagement_score,
                content_row_id=p.content_row_id,
                fetched_at=p.fetched_at,
            )
            for p in performance
        ],
    )


# ── Tag Management ───────────────────────────────────────────────────────


@router.put("/media/{media_id}/tags")
async def update_media_tags(
    media_id: int,
    req: MediaTagUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Add and/or remove tags from a media item."""
    result = await session.execute(select(MediaCatalog).where(MediaCatalog.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Remove tags
    if req.remove:
        await session.execute(
            sa_delete(MediaTag).where(MediaTag.media_id == media_id, MediaTag.tag.in_(req.remove))
        )

    # Add tags (skip duplicates)
    if req.add:
        existing_result = await session.execute(
            select(MediaTag.tag).where(MediaTag.media_id == media_id)
        )
        existing_tags = {row[0] for row in existing_result}
        for tag_name in req.add:
            if tag_name not in existing_tags:
                session.add(
                    MediaTag(
                        media_id=media_id,
                        tag=tag_name,
                        confidence=1.0,
                        source="manual",
                    )
                )

    await session.commit()

    # Return updated tag list
    tags_result = await session.execute(select(MediaTag).where(MediaTag.media_id == media_id))
    tags = tags_result.scalars().all()

    return {
        "tags": [
            MediaTagResponse(
                id=t.id, tag=t.tag, confidence=t.confidence, source=t.source
            ).model_dump()
            for t in tags
        ]
    }


# ── Delete ───────────────────────────────────────────────────────────────


@router.delete("/media/{media_id}", response_model=MediaDeleteResponse)
async def delete_media(
    media_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a media item, its tags, and clean up local files."""
    result = await session.execute(select(MediaCatalog).where(MediaCatalog.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Clean up files (ignore if already gone)
    for path_str in (media.local_path, media.thumbnail_path):
        if path_str:
            p = Path(path_str)
            if p.exists():
                p.unlink()

    # Remove related tags and performance records
    await session.execute(sa_delete(MediaTag).where(MediaTag.media_id == media_id))
    await session.execute(sa_delete(MediaPerformance).where(MediaPerformance.media_id == media_id))

    # Remove the catalog entry
    await session.delete(media)
    await session.commit()

    return MediaDeleteResponse(deleted=True, id=media_id)


# ── Adaptation ───────────────────────────────────────────────────────────

PLATFORM_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    "instagram": {
        "post": (1080, 1080),
        "story": (1080, 1920),
    },
    "facebook": {
        "post": (1200, 630),
        "story": (1080, 1920),
    },
    "tiktok": {
        "story": (1080, 1920),
    },
    "linkedin": {
        "post": (1200, 627),
    },
}


class AdaptRequest(BaseModel):
    platforms: list[str]
    formats: list[str]


def _smart_crop(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop and resize to target dimensions."""
    img_w, img_h = image.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        # Image is wider — crop sides
        new_w = int(img_h * target_ratio)
        left = (img_w - new_w) // 2
        crop_box = (left, 0, left + new_w, img_h)
    else:
        # Image is taller — crop top/bottom
        new_h = int(img_w / target_ratio)
        top = (img_h - new_h) // 2
        crop_box = (0, top, img_w, top + new_h)

    cropped = image.crop(crop_box)
    return cropped.resize((target_w, target_h), Image.LANCZOS)


@router.post("/media/{media_id}/adapt")
async def adapt_media(
    media_id: int,
    req: AdaptRequest,
    session: AsyncSession = Depends(get_db),
):
    """Generate platform-specific image versions using smart crop."""
    result = await session.execute(select(MediaCatalog).where(MediaCatalog.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    src_path = Path(media.local_path)
    if not src_path.exists():
        raise HTTPException(status_code=400, detail="Source image file not found")

    # Ensure adapted directory exists
    adapted_dir = src_path.parent / "adapted"
    adapted_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(src_path) as src_img:
        adapted_results = []
        for platform in req.platforms:
            dims = PLATFORM_DIMENSIONS.get(platform, {})
            for fmt in req.formats:
                target = dims.get(fmt)
                if not target:
                    continue
                target_w, target_h = target

                # Smart crop + resize
                adapted_img = _smart_crop(src_img, target_w, target_h)

                # Save
                out_name = f"{media_id}_{platform}_{fmt}.jpg"
                out_path = adapted_dir / out_name
                adapted_img.save(out_path, format="JPEG", quality=90)

                # DB record
                record = MediaAdapted(
                    media_id=media_id,
                    platform=platform,
                    format=fmt,
                    adapted_path=str(out_path),
                    width=target_w,
                    height=target_h,
                )
                session.add(record)
                await session.flush()

                adapted_results.append(
                    {
                        "id": record.id,
                        "platform": platform,
                        "format": fmt,
                        "adapted_path": str(out_path),
                        "width": target_w,
                        "height": target_h,
                    }
                )

    await session.commit()
    return {"adapted": adapted_results}
