"""File upload endpoint."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.auth import get_current_user
from api.schemas import UploadResponse

router = APIRouter(prefix="/api", tags=["upload"], dependencies=[Depends(get_current_user)])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
UPLOAD_DIR = Path("/tmp/postiz_uploads")


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile, _user: dict = Depends(get_current_user)):
    """Upload a media file for use in posts."""
    if not file.content_type or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    content = await file.read()
    size = len(content)

    max_size = MAX_VIDEO_SIZE if file.content_type.startswith("video/") else MAX_IMAGE_SIZE
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size} bytes. Max: {max_size} bytes.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / filename

    filepath.write_bytes(content)

    return UploadResponse(
        url=str(filepath),
        content_type=file.content_type,
        size=size,
    )
