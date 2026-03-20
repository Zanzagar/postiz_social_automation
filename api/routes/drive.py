"""Google Drive media import endpoints."""

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db, get_settings
from api.models import MediaCatalog, MediaTag
from api.routes.media import THUMBNAIL_SIZE, _classify_media_tags, _upload_to_postiz

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

router = APIRouter(
    prefix="/api/media/drive",
    tags=["drive"],
    dependencies=[Depends(get_current_user)],
)


def get_drive_service():
    """Build a Google Drive API v3 service using service account credentials."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    settings = get_settings()
    creds = Credentials.from_service_account_file(
        settings.google_sheets_credentials, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _download_drive_file(service, file_id: str) -> bytes:
    """Download file content from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    content = request.execute()
    return content


# ── Browse ───────────────────────────────────────────────────────────


@router.get("/browse")
async def browse_drive(
    folder_id: str = Query(...),
    page_token: str | None = None,
):
    """List image files in a Google Drive folder."""
    try:
        service = get_drive_service()
    except Exception as e:
        logger.error("Drive service init failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drive auth error: {e}")

    try:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        result = (
            service.files()
            .list(
                q=query,
                fields="files(id,name,mimeType,size,thumbnailLink),nextPageToken",
                pageSize=20,
                pageToken=page_token,
            )
            .execute()
        )

        files = [
            {
                "id": f["id"],
                "name": f["name"],
                "mime_type": f.get("mimeType", ""),
                "size": int(f.get("size", 0)),
                "thumbnail_link": f.get("thumbnailLink"),
            }
            for f in result.get("files", [])
        ]

        return {
            "files": files,
            "next_page_token": result.get("nextPageToken"),
        }
    except Exception as e:
        logger.error("Drive browse failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drive API error: {e}")


# ── Import ───────────────────────────────────────────────────────────


class DriveImportRequest(BaseModel):
    file_ids: list[str]


import_router = APIRouter(
    prefix="/api/media",
    tags=["drive"],
    dependencies=[Depends(get_current_user)],
)


@import_router.post("/import-drive")
async def import_from_drive(
    req: DriveImportRequest,
    session: AsyncSession = Depends(get_db),
):
    """Import files from Google Drive into the media catalog."""
    if not req.file_ids:
        return {"imported": 0, "errors": [], "skipped": []}

    # Check already-imported files
    existing_result = await session.execute(
        select(MediaCatalog.original_url).where(MediaCatalog.source == "drive")
    )
    existing_urls = {row[0] for row in existing_result if row[0]}

    try:
        service = get_drive_service()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drive auth error: {e}")

    imported = 0
    errors: list[dict] = []
    skipped: list[str] = []
    media_dir = Path("media")
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "thumbnails").mkdir(exist_ok=True)

    for file_id in req.file_ids:
        drive_url = f"drive://{file_id}"

        # Skip already imported
        if drive_url in existing_urls:
            skipped.append(file_id)
            continue

        try:
            # Get file metadata
            meta = service.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
            filename = meta.get("name", f"{file_id}.jpg")
            mime_type = meta.get("mimeType", "image/jpeg")

            # Download
            content = _download_drive_file(service, file_id)

            # Save locally
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
            stored_name = f"{uuid.uuid4().hex}.{ext}"
            file_path = media_dir / stored_name
            file_path.write_bytes(content)

            # Dimensions
            width = height = None
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception:
                pass

            # Thumbnail
            thumb_path = media_dir / "thumbnails" / f"thumb_{stored_name}"
            try:
                with Image.open(file_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                    img.save(thumb_path)
            except Exception:
                thumb_path = None

            # Postiz upload
            postiz_id = None
            try:
                postiz_id = _upload_to_postiz(file_path)
            except Exception:
                pass

            # AI tagging
            tag_results = _classify_media_tags(str(file_path))

            # DB insert
            catalog = MediaCatalog(
                filename=filename,
                original_url=drive_url,
                local_path=str(file_path),
                postiz_media_id=postiz_id,
                thumbnail_path=str(thumb_path) if thumb_path else None,
                mime_type=mime_type,
                width=width,
                height=height,
                file_size=len(content),
                tags=json.dumps([t["tag"] for t in tag_results]) if tag_results else None,
                source="drive",
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

            imported += 1

        except Exception as e:
            logger.warning("Drive import failed for %s: %s", file_id, e, exc_info=True)
            errors.append({"file_id": file_id, "error": str(e)})

    await session.commit()
    return {"imported": imported, "errors": errors, "skipped": skipped}
