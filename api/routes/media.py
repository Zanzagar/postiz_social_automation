"""Media catalog endpoints — upload, import, browse."""

import json
import logging
import subprocess
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db, get_settings
from api.models import MediaCatalog, MediaTag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media"], dependencies=[Depends(get_current_user)])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
THUMBNAIL_SIZE = (200, 200)


def _get_media_dir() -> Path:
    """Return the media storage directory, creating it if needed."""
    media_dir = Path("media")
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "thumbnails").mkdir(exist_ok=True)
    return media_dir


def _generate_thumbnail(src_path: Path, thumb_path: Path) -> None:
    """Generate a 200x200 thumbnail maintaining aspect ratio."""
    with Image.open(src_path) as img:
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        img.save(thumb_path)


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
            ["claude", "-p", prompt, "--image", image_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            # Strip markdown fences if present
            output = result.stdout.strip()
            if output.startswith("```"):
                output = output.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(output)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
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
    """Shared logic: save file, thumbnail, Postiz upload, AI tag, DB insert."""
    media_dir = _get_media_dir()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = media_dir / stored_name
    file_path.write_bytes(content)

    # Image dimensions
    width = height = None
    try:
        with Image.open(file_path) as img:
            width, height = img.size
    except Exception:
        pass

    # Thumbnail
    thumb_path = media_dir / "thumbnails" / f"thumb_{stored_name}"
    try:
        _generate_thumbnail(file_path, thumb_path)
    except Exception:
        logger.warning("Thumbnail generation failed for %s", stored_name, exc_info=True)
        thumb_path = None

    # Postiz upload (non-blocking, optional)
    postiz_id = None
    try:
        postiz_id = _upload_to_postiz(file_path)
    except Exception:
        logger.warning("Postiz upload failed for %s", stored_name, exc_info=True)

    # AI tagging
    tag_results = _classify_media_tags(str(file_path))

    # DB insert
    catalog = MediaCatalog(
        filename=filename,
        original_url=original_url,
        local_path=str(file_path),
        postiz_media_id=postiz_id,
        thumbnail_path=str(thumb_path) if thumb_path else None,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=len(content),
        tags=json.dumps([t["tag"] for t in tag_results]) if tag_results else None,
        source=source,
    )
    session.add(catalog)
    await session.flush()

    # Insert tags
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
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_TYPES)}",
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
