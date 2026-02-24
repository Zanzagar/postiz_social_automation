"""Mode 1: Enhance Pipeline — orchestrate Sheet → Validate → Generate → Postiz."""

import logging
from dataclasses import dataclass

from content_engine.generator import CaptionGenerator
from content_engine.models import ContentStatus
from content_engine.postiz import PostizClient
from content_engine.sheets import SheetsClient
from content_engine.validator import ContentValidator

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summary of a pipeline run."""

    processed: int = 0
    errors: int = 0
    skipped: int = 0


def enhance_pipeline(
    *,
    sheets: SheetsClient,
    postiz: PostizClient,
    generator: CaptionGenerator,
    validator: ContentValidator,
) -> PipelineResult:
    """Run the Mode 1 Enhance Pipeline.

    Fetches 'ready' rows from Google Sheets, validates them,
    generates AI captions, creates Postiz drafts, and updates
    the Sheet with results.

    Partial failures are handled per-row: if one row fails,
    the rest continue processing.
    """
    result = PipelineResult()

    # Build platform → integration ID map from Postiz
    integrations = postiz.list_integrations()
    platform_map: dict[str, str] = {i["platform"]: i["id"] for i in integrations}

    ready_rows = sheets.get_rows_by_status(ContentStatus.READY)
    logger.info("Found %d ready rows to process", len(ready_rows))

    for row in ready_rows:
        try:
            # Validate
            is_valid, error = validator.validate_row(row)
            if not is_valid:
                sheets.update_status(row.row_number, ContentStatus.ERROR, error)
                logger.warning("Row %d invalid: %s", row.row_number, error)
                result.errors += 1
                continue

            # Generate AI captions
            captions = generator.generate_captions(row)
            sheets.update_captions(row.row_number, captions)

            # Create Postiz drafts for connected platforms
            draft_ids: list[str] = []
            for platform, caption in captions.items():
                platform_key = platform.value
                if platform_key not in platform_map:
                    logger.info(
                        "Skipping %s for row %d — not connected in Postiz",
                        platform_key,
                        row.row_number,
                    )
                    continue

                draft = postiz.create_draft_post(
                    content=caption,
                    platform_ids=[platform_map[platform_key]],
                    media_url=str(row.media_url) if row.media_url else None,
                )
                draft_ids.append(draft["id"])
                logger.info(
                    "Created draft for %s (row %d): %s",
                    platform_key,
                    row.row_number,
                    draft["id"],
                )

            # Record Postiz IDs and update status
            if draft_ids:
                sheets.update_postiz_ids(row.row_number, ",".join(draft_ids))
            sheets.update_status(row.row_number, ContentStatus.PENDING_APPROVAL)
            result.processed += 1
            logger.info("Row %d processed successfully", row.row_number)

        except Exception as e:
            sheets.update_status(row.row_number, ContentStatus.ERROR, str(e))
            logger.error("Row %d failed: %s", row.row_number, e)
            result.errors += 1

    logger.info(
        "Pipeline complete: %d processed, %d errors, %d skipped",
        result.processed,
        result.errors,
        result.skipped,
    )
    return result
