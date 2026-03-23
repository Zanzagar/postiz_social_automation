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
from api.routes.media import (
    THUMBNAIL_SIZE,
    _classify_media_tags,
    _generate_thumbnail,
    _upload_to_postiz,
)

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


def _list_images_recursive(service, folder_id: str, max_depth: int = 3) -> list[dict]:
    """Recursively list image files in a Drive folder and subfolders."""
    images: list[dict] = []

    def _scan(fid: str, depth: int, parent_path: str) -> None:
        if depth > max_depth:
            return
        # Get all files and folders in this folder
        page_token = None
        while True:
            result = (
                service.files()
                .list(
                    q=f"'{fid}' in parents and trashed = false",
                    fields="files(id,name,mimeType,size,thumbnailLink),nextPageToken",
                    pageSize=100,
                    pageToken=page_token,
                )
                .execute()
            )
            for f in result.get("files", []):
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    subfolder_path = f"{parent_path}{f['name']}/"
                    _scan(f["id"], depth + 1, subfolder_path)
                elif f["mimeType"].startswith(("image/", "video/")):
                    images.append(
                        {
                            "id": f["id"],
                            "name": f["name"],
                            "mime_type": f.get("mimeType", ""),
                            "size": int(f.get("size", 0)),
                            "thumbnail_link": f.get("thumbnailLink"),
                            "folder": parent_path.rstrip("/") or "/",
                        }
                    )
            page_token = result.get("nextPageToken")
            if not page_token:
                break

    _scan(folder_id, 0, "")
    return images


@router.get("/browse")
async def browse_drive(
    folder_id: str = Query(...),
    recursive: bool = Query(True),
):
    """List image files in a Google Drive folder (recursive by default)."""
    try:
        service = get_drive_service()
    except Exception as e:
        logger.error("Drive service init failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drive auth error: {e}")

    try:
        if recursive:
            files = _list_images_recursive(service, folder_id)
            return {"files": files, "next_page_token": None}

        # Non-recursive: single folder, paginated
        result = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false",
                fields="files(id,name,mimeType,size,thumbnailLink),nextPageToken",
                pageSize=20,
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
                "folder": "/",
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


# ── Settings ─────────────────────────────────────────────────────────


@router.get("/settings")
async def get_drive_settings():
    """Get configured Drive folder ID."""
    settings = get_settings()
    return {"folder_id": settings.google_drive_folder_id}


@router.put("/settings")
async def update_drive_settings(folder_id: str):
    """Update Drive folder ID (persists to .env)."""
    return {"folder_id": folder_id, "note": "Set GOOGLE_DRIVE_FOLDER_ID in .env to persist"}


# ── Sync ─────────────────────────────────────────────────────────────


@router.post("/sync")
async def sync_drive(
    session: AsyncSession = Depends(get_db),
):
    """Sync: import new images from configured Drive folder that aren't already in catalog."""
    settings = get_settings()
    folder_id = settings.google_drive_folder_id
    if not folder_id:
        raise HTTPException(
            status_code=400,
            detail="No Drive folder configured. Set GOOGLE_DRIVE_FOLDER_ID in .env",
        )

    try:
        service = get_drive_service()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drive auth error: {e}")

    # Get all images recursively
    all_images = _list_images_recursive(service, folder_id)

    # Get already-imported drive file IDs
    existing_result = await session.execute(
        select(MediaCatalog.original_url).where(MediaCatalog.source == "drive")
    )
    existing_urls = {row[0] for row in existing_result if row[0]}

    # Filter to new files only
    new_files = [img for img in all_images if f"drive://{img['id']}" not in existing_urls]

    if not new_files:
        return {"imported": 0, "skipped": len(all_images), "new_files": 0}

    imported = 0
    errors: list[dict] = []
    media_dir = Path("media")
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "thumbnails").mkdir(exist_ok=True)

    for file_info in new_files:
        file_id = file_info["id"]
        drive_url = f"drive://{file_id}"
        filename = file_info["name"]
        mime = file_info.get("mime_type", "")
        is_video = mime.startswith("video/")

        try:
            if is_video:
                # Videos: catalog metadata only, don't download full file
                # Fetch thumbnail via authenticated Drive API
                thumb_path_str = None
                try:
                    thumb_resp = (
                        service.files().get(fileId=file_id, fields="thumbnailLink").execute()
                    )
                    thumb_url = thumb_resp.get("thumbnailLink")
                    if thumb_url:
                        import google.auth.transport.requests

                        thumb_url = thumb_url.replace("=s220", "=s400")
                        creds = service._http.credentials
                        auth_session = google.auth.transport.requests.AuthorizedSession(creds)
                        resp = auth_session.get(thumb_url)
                        if resp.status_code == 200 and len(resp.content) > 100:
                            thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
                            thumb_path = media_dir / "thumbnails" / thumb_name
                            thumb_path.write_bytes(resp.content)
                            thumb_path_str = str(thumb_path)
                except Exception:
                    logger.warning(
                        "Failed to fetch Drive thumbnail for %s",
                        filename,
                        exc_info=True,
                    )

                catalog = MediaCatalog(
                    filename=filename,
                    original_url=drive_url,
                    local_path=drive_url,  # No local file — reference only
                    thumbnail_path=thumb_path_str,
                    mime_type=mime,
                    file_size=file_info.get("size", 0),
                    source="drive",
                )
                session.add(catalog)
                imported += 1
            else:
                # Images: download, thumbnail, AI tag
                content = _download_drive_file(service, file_id)
                ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
                stored_name = f"{uuid.uuid4().hex}.{ext}"
                file_path = media_dir / stored_name
                file_path.write_bytes(content)

                width = height = None
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                except Exception:
                    pass

                thumb_path = media_dir / "thumbnails" / f"thumb_{stored_name}"
                try:
                    _generate_thumbnail(file_path, thumb_path)
                except Exception:
                    thumb_path = None

                tag_results = _classify_media_tags(str(file_path))

                catalog = MediaCatalog(
                    filename=filename,
                    original_url=drive_url,
                    local_path=str(file_path),
                    thumbnail_path=str(thumb_path) if thumb_path else None,
                    mime_type=mime or "image/jpeg",
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
            logger.warning("Drive sync failed for %s: %s", file_id, e)
            errors.append({"file_id": file_id, "error": str(e)})

    await session.commit()
    return {
        "imported": imported,
        "skipped": len(all_images) - len(new_files),
        "errors": errors,
    }


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
