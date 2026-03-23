"""Media catalog health check — keeps DB and filesystem in sync."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db
from api.models import MediaCatalog, MediaPerformance, MediaTag

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["media-health"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/media-health")
async def media_health(
    session: AsyncSession = Depends(get_db),
):
    """Check consistency between media catalog DB and local files."""
    result = await session.execute(select(MediaCatalog))
    all_media = result.scalars().all()

    healthy = 0
    missing_file = []
    missing_thumb = []
    drive_refs = 0

    for m in all_media:
        is_drive_ref = m.local_path and m.local_path.startswith("drive://")

        if is_drive_ref:
            drive_refs += 1
            healthy += 1
            continue

        file_ok = m.local_path and Path(m.local_path).exists()
        thumb_ok = not m.thumbnail_path or Path(m.thumbnail_path).exists()

        if not file_ok:
            missing_file.append({"id": m.id, "filename": m.filename})
        if not thumb_ok:
            missing_thumb.append({"id": m.id, "filename": m.filename})
        if file_ok:
            healthy += 1

    # Check for orphaned files on disk
    db_paths = set()
    for m in all_media:
        if m.local_path and not m.local_path.startswith("drive://"):
            db_paths.add(Path(m.local_path).name)
        if m.thumbnail_path:
            db_paths.add(Path(m.thumbnail_path).name)

    media_dir = Path("media")
    orphan_files = []
    if media_dir.exists():
        for f in media_dir.glob("*.*"):
            if f.name not in db_paths:
                orphan_files.append(f.name)
        for f in (media_dir / "thumbnails").glob("*.*"):
            if f.name not in db_paths:
                orphan_files.append(f"thumbnails/{f.name}")

    return {
        "total": len(all_media),
        "healthy": healthy,
        "drive_refs": drive_refs,
        "missing_file": missing_file,
        "missing_thumb": missing_thumb,
        "orphan_files": len(orphan_files),
    }


@router.post("/media-cleanup")
async def media_cleanup(
    remove_missing: bool = Query(False),
    remove_orphans: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    """Clean up inconsistencies: remove DB entries with missing files, delete orphaned files."""
    removed_entries = 0
    removed_orphans = 0

    if remove_missing:
        result = await session.execute(select(MediaCatalog))
        for m in result.scalars().all():
            if m.local_path and m.local_path.startswith("drive://"):
                continue
            if m.local_path and not Path(m.local_path).exists():
                await session.execute(sa_delete(MediaTag).where(MediaTag.media_id == m.id))
                await session.execute(
                    sa_delete(MediaPerformance).where(MediaPerformance.media_id == m.id)
                )
                await session.delete(m)
                removed_entries += 1

    if remove_orphans:
        # Rebuild path set
        result = await session.execute(select(MediaCatalog))
        db_paths = set()
        for m in result.scalars().all():
            if m.local_path and not m.local_path.startswith("drive://"):
                db_paths.add(Path(m.local_path).name)
            if m.thumbnail_path:
                db_paths.add(Path(m.thumbnail_path).name)

        media_dir = Path("media")
        if media_dir.exists():
            for f in media_dir.glob("*.*"):
                if f.name not in db_paths:
                    f.unlink()
                    removed_orphans += 1
            for f in (media_dir / "thumbnails").glob("*.*"):
                if f.name not in db_paths:
                    f.unlink()
                    removed_orphans += 1

    await session.commit()
    return {
        "removed_entries": removed_entries,
        "removed_orphans": removed_orphans,
    }
