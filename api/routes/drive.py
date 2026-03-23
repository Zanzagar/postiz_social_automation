"""Google Drive as central media repository.

All media (uploads, imports, social scrapes) are stored in Google Drive.
The local DB holds metadata, tags, and engagement data only.
Thumbnails are cached locally for fast grid display.
"""

import io
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db, get_settings
from api.models import MediaCatalog

logger = logging.getLogger(__name__)

# drive.file: can create/manage files the SA created; can read shared files
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

THUMB_DIR = Path("media/thumbnails")

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


def _get_or_create_subfolder(service, parent_id: str, name: str) -> str:
    """Get or create a named subfolder under parent_id. Returns folder ID."""
    result = (
        service.files()
        .list(
            q=f"'{parent_id}' in parents and name='{name}' "
            "and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)",
        )
        .execute()
    )
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    # Create
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_to_drive(
    content: bytes,
    filename: str,
    mime_type: str,
    subfolder: str = "Uploads",
) -> dict:
    """Upload a file to Drive under the configured root folder.

    Returns {"id": file_id, "name": filename, "webViewLink": url}.
    """
    from googleapiclient.http import MediaInMemoryUpload

    settings = get_settings()
    if not settings.google_drive_folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID not configured")

    service = get_drive_service()
    folder_id = _get_or_create_subfolder(service, settings.google_drive_folder_id, subfolder)

    file_meta = {"name": filename, "parents": [folder_id]}
    media = MediaInMemoryUpload(content, mimetype=mime_type, resumable=False)
    result = (
        service.files()
        .create(body=file_meta, media_body=media, fields="id,name,webViewLink")
        .execute()
    )
    return result


def _fetch_drive_thumbnail(service, file_id: str) -> str | None:
    """Fetch thumbnail from Drive API and cache locally. Returns local path or None."""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    try:
        meta = service.files().get(fileId=file_id, fields="thumbnailLink").execute()
        thumb_url = meta.get("thumbnailLink")
        if not thumb_url:
            return None

        import google.auth.transport.requests

        thumb_url = thumb_url.replace("=s220", "=s400")
        creds = service._http.credentials
        auth_session = google.auth.transport.requests.AuthorizedSession(creds)
        resp = auth_session.get(thumb_url)
        if resp.status_code == 200 and len(resp.content) > 100:
            thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
            thumb_path = THUMB_DIR / thumb_name
            thumb_path.write_bytes(resp.content)
            return str(thumb_path)
    except Exception:
        logger.warning("Failed to fetch Drive thumbnail for %s", file_id, exc_info=True)
    return None


def _download_drive_file(service, file_id: str) -> bytes:
    """Download file content from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    content = request.execute()
    return content


# ── Proxy (serve Drive files through backend) ───────────────────────


@router.get("/file/{file_id}")
async def proxy_drive_file(file_id: str):
    """Proxy a Drive file through the backend for authenticated access."""
    try:
        service = get_drive_service()
        meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
        content = _download_drive_file(service, file_id)
        return StreamingResponse(
            io.BytesIO(content),
            media_type=meta.get("mimeType", "application/octet-stream"),
            headers={"Content-Disposition": f'inline; filename="{meta.get("name", "file")}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Drive file not found: {e}")


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
    """Sync: catalog new files from configured Drive folder (metadata + thumbnail only)."""
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

    all_files = _list_images_recursive(service, folder_id)

    existing_result = await session.execute(
        select(MediaCatalog.original_url).where(MediaCatalog.source == "drive")
    )
    existing_urls = {row[0] for row in existing_result if row[0]}

    new_files = [f for f in all_files if f"drive://{f['id']}" not in existing_urls]
    if not new_files:
        return {"imported": 0, "skipped": len(all_files), "errors": []}

    imported = 0
    errors: list[dict] = []

    for file_info in new_files:
        file_id = file_info["id"]
        try:
            thumb_path = _fetch_drive_thumbnail(service, file_id)
            catalog = MediaCatalog(
                filename=file_info["name"],
                original_url=f"drive://{file_id}",
                local_path=f"drive://{file_id}",
                thumbnail_path=thumb_path,
                mime_type=file_info.get("mime_type", ""),
                file_size=file_info.get("size", 0),
                source="drive",
            )
            session.add(catalog)
            imported += 1
        except Exception as e:
            logger.warning("Drive sync failed for %s: %s", file_id, e)
            errors.append({"file_id": file_id, "error": str(e)})

    await session.commit()
    return {
        "imported": imported,
        "skipped": len(all_files) - len(new_files),
        "errors": errors,
    }


# ── Import (selective from browse) ──────────────────────────────────


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
    """Catalog selected Drive files (metadata + thumbnail only)."""
    if not req.file_ids:
        return {"imported": 0, "errors": [], "skipped": []}

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

    for file_id in req.file_ids:
        drive_url = f"drive://{file_id}"
        if drive_url in existing_urls:
            skipped.append(file_id)
            continue

        try:
            meta = service.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
            thumb_path = _fetch_drive_thumbnail(service, file_id)

            catalog = MediaCatalog(
                filename=meta.get("name", f"{file_id}"),
                original_url=drive_url,
                local_path=drive_url,
                thumbnail_path=thumb_path,
                mime_type=meta.get("mimeType", ""),
                file_size=int(meta.get("size", 0)),
                source="drive",
            )
            session.add(catalog)
            imported += 1
        except Exception as e:
            logger.warning("Drive import failed for %s: %s", file_id, e)
            errors.append({"file_id": file_id, "error": str(e)})

    await session.commit()
    return {"imported": imported, "errors": errors, "skipped": skipped}
