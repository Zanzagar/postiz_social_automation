"""Bidirectional sync between Google Sheets and SQLite.

Import: Poll Sheet for READY rows → insert into SQLite as DRAFT.
Export: Push status/postiz_id changes back to Sheet for sheet-originated rows.
"""

import json
import logging

from api.repositories.content import ContentRepository
from content_engine.models import ContentStatus
from content_engine.sheets import SheetsClient

logger = logging.getLogger(__name__)


class SheetsSyncAdapter:
    """Syncs content between Google Sheets and SQLite."""

    def __init__(self, sheets_client: SheetsClient, repo: ContentRepository):
        self.sheets = sheets_client
        self.repo = repo

    async def import_ready_rows(self) -> list[int]:
        """Import all READY rows from Sheet to SQLite. Returns list of new row IDs."""
        rows = self.sheets.get_rows_by_status(ContentStatus.READY)
        imported_ids = []

        for row in rows:
            existing = await self.repo.find_by_sheet_row(row.row_number)
            if existing:
                continue

            # Convert Pydantic model → dict for SQLAlchemy
            platforms_json = json.dumps({p.value: v for p, v in row.platforms.items()})
            captions_json = json.dumps({p.value: v for p, v in row.captions.items()})

            content_row = await self.repo.create_content_row(
                {
                    "date": row.date,
                    "pillar": row.content_pillar if row.content_pillar else None,
                    "raw_text": row.raw_text,
                    "media_url": str(row.media_url) if row.media_url else None,
                    "platforms": platforms_json,
                    "status": ContentStatus.DRAFT.value,
                    "captions": captions_json,
                    "source": "sheet",
                    "sheet_row_number": row.row_number,
                }
            )

            self.sheets.update_status(row.row_number, ContentStatus.DRAFT)
            imported_ids.append(content_row.id)

        return imported_ids

    async def export_status_updates(self) -> int:
        """Push status changes to Sheet for sheet-originated rows. Returns count."""
        rows = await self.repo.get_rows_needing_sheet_sync()
        synced = 0

        for row in rows:
            if row.sheet_row_number is None:
                continue

            error_msg = row.feedback if row.status == "error" else None
            self.sheets.update_status(
                row.sheet_row_number,
                ContentStatus(row.status),
                error_msg,
            )

            if row.postiz_ids:
                postiz_list = json.loads(row.postiz_ids)
                postiz_str = (
                    ",".join(postiz_list) if isinstance(postiz_list, list) else str(postiz_list)
                )
                self.sheets.update_postiz_ids(
                    row.sheet_row_number,
                    postiz_str,
                    row.posted_at,
                )

            await self.repo.mark_sheet_synced(row.id)
            synced += 1

        return synced

    async def run_sync_once(self) -> dict:
        """Run one import+export cycle. Returns summary dict."""
        try:
            imported = await self.import_ready_rows()
            exported = await self.export_status_updates()
            if imported:
                logger.info("Imported %d rows from Sheet", len(imported))
            if exported:
                logger.info("Exported %d status updates to Sheet", exported)
            return {"imported": len(imported), "exported": exported, "error": None}
        except Exception as e:
            logger.exception("Sheet sync error")
            return {"imported": 0, "exported": 0, "error": str(e)}
