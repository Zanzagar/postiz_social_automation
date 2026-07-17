"""Resolve a content row's media to a publicly reachable URL for Postiz.

Postiz downloads media server-side, so any URL handed to it must be
reachable from the public internet. Local uploads (``/media/...``) are
not; Google Drive files are made reachable by idempotently granting an
anyone-with-link reader permission and returning the direct-download URL
form (which PostizClient already normalizes before upload).
"""

import asyncio
import json
import re

from api.models import MediaCatalog

NOT_PUBLIC_MESSAGE = (
    "Media isn't publicly reachable — import it to Google Drive first, then reattach"
)

_DRIVE_PROXY_RE = re.compile(r"^/api/media/drive/file/([A-Za-z0-9_-]+)/?$")
_DRIVE_LOCAL_PREFIX = "drive://"


class MediaNotPublicError(Exception):
    """The row's media cannot be fetched by Postiz from the public internet."""

    def __init__(self, reason: str = NOT_PUBLIC_MESSAGE) -> None:
        super().__init__(reason)


def _direct_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def _ensure_public_drive_permission(file_id: str) -> None:
    """Idempotently grant anyone-with-link reader access to a Drive file.

    'Already exists'/duplicate errors are swallowed (the goal state is
    already met); anything else propagates to the caller.
    """
    from api.routes.drive import get_drive_service

    service = get_drive_service()
    try:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception as e:
        message = str(e).lower()
        if "already exists" in message or "duplicate" in message:
            return
        raise


async def _resolve_drive_file(file_id: str) -> str:
    # Blocking Google API call — keep it off the event loop.
    await asyncio.to_thread(_ensure_public_drive_permission, file_id)
    return _direct_download_url(file_id)


async def resolve_public_media_url(session, row) -> str | None:
    """Map a content row's media to a publicly reachable URL.

    - http(s) media_url: returned as-is (PostizClient normalizes Drive
      sharing links itself).
    - Drive-proxy media_url (``/api/media/drive/file/{fid}``) or a first
      media_catalog_ids item stored as ``drive://{fid}``: ensure the file
      is link-shareable, return its direct-download URL.
    - Any other local-only media: raise :class:`MediaNotPublicError`.
    - No media at all: return None.
    """
    media_url = (row.media_url or "").strip()
    if media_url.startswith(("http://", "https://")):
        return media_url
    if media_url:
        match = _DRIVE_PROXY_RE.match(media_url)
        if match is None:
            raise MediaNotPublicError()
        return await _resolve_drive_file(match.group(1))

    raw_ids = row.media_catalog_ids
    if not raw_ids:
        return None
    try:
        catalog_ids = json.loads(raw_ids)
    except (json.JSONDecodeError, TypeError):
        # Unparseable but non-empty — same conservative stance as the
        # NO-ALT gate's _has_media: treat as media we cannot serve.
        raise MediaNotPublicError() from None
    if not isinstance(catalog_ids, list) or not catalog_ids:
        return None

    media = await session.get(MediaCatalog, catalog_ids[0])
    if media is None:
        raise MediaNotPublicError()
    local_path = media.local_path or ""
    if local_path.startswith(_DRIVE_LOCAL_PREFIX):
        return await _resolve_drive_file(local_path[len(_DRIVE_LOCAL_PREFIX) :])
    raise MediaNotPublicError()
