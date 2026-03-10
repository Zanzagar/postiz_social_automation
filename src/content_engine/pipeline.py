"""Content pipelines — Enhance (Mode 1), Re-prompt, Suggest (Mode 2), and Learn workflows."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from content_engine.generator import CaptionGenerator
from content_engine.intelligence import ContentIntelligence
from content_engine.models import ContentPillar, ContentStatus
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


def reprompt_pipeline(
    *,
    sheets: SheetsClient,
    postiz: PostizClient,
    generator: CaptionGenerator,
) -> PipelineResult:
    """Run the re-prompt pipeline for rows with staff feedback.

    Fetches 'pending_approval' rows that have feedback, regenerates
    captions with the feedback context, creates fresh Postiz drafts,
    and clears the feedback column.
    """
    result = PipelineResult()

    integrations = postiz.list_integrations()
    platform_map: dict[str, str] = {i["platform"]: i["id"] for i in integrations}

    feedback_rows = sheets.get_rows_with_feedback()
    logger.info("Found %d rows with feedback to re-process", len(feedback_rows))

    for row in feedback_rows:
        try:
            # Regenerate captions with feedback
            captions = generator.generate_captions(row, feedback=row.feedback)
            sheets.update_captions(row.row_number, captions)

            # Create fresh Postiz drafts
            draft_ids: list[str] = []
            for platform, caption in captions.items():
                platform_key = platform.value
                if platform_key not in platform_map:
                    continue

                draft = postiz.create_draft_post(
                    content=caption,
                    platform_ids=[platform_map[platform_key]],
                    media_url=str(row.media_url) if row.media_url else None,
                )
                draft_ids.append(draft["id"])

            if draft_ids:
                sheets.update_postiz_ids(row.row_number, ",".join(draft_ids))

            # Clear feedback and keep status as pending_approval
            sheets.clear_feedback(row.row_number)
            sheets.update_status(row.row_number, ContentStatus.PENDING_APPROVAL)
            result.processed += 1
            logger.info("Row %d re-prompted successfully", row.row_number)

        except Exception as e:
            sheets.update_status(row.row_number, ContentStatus.ERROR, str(e))
            logger.error("Row %d re-prompt failed: %s", row.row_number, e)
            result.errors += 1

    logger.info(
        "Re-prompt complete: %d processed, %d errors",
        result.processed,
        result.errors,
    )
    return result


def suggest_pipeline(
    *,
    sheets: SheetsClient,
    postiz: PostizClient,
    generator: CaptionGenerator,
    intelligence: ContentIntelligence,
    days_ahead: int = 14,
) -> PipelineResult:
    """Run the Mode 2 Suggestion Pipeline.

    Analyzes calendar gaps and pillar balance via ContentIntelligence,
    generates AI suggestions, and writes them to the Suggestions tab.
    """
    result = PipelineResult()

    try:
        # Analyze current content state
        gaps = intelligence.analyze_calendar_gaps(days_ahead=days_ahead)
        pillar_balance_raw = intelligence.analyze_pillar_balance()
        events = intelligence.get_upcoming_events(days_ahead=7)

        # Convert gaps to date strings for the generator
        gap_dates = [g["date"] for g in gaps]

        # Simplify pillar balance: pillar_name -> actual_pct
        pillar_balance: dict[str, float] = {}
        for pillar, stats in pillar_balance_raw.items():
            pillar_name = pillar.value if isinstance(pillar, ContentPillar) else str(pillar)
            pillar_balance[pillar_name] = stats["actual"]

        logger.info(
            "Analysis: %d calendar gaps, %d pillars tracked, %d upcoming events",
            len(gap_dates),
            len(pillar_balance),
            len(events),
        )

        # Generate AI suggestions
        suggestions = generator.generate_suggestions(
            calendar_gaps=gap_dates,
            pillar_balance=pillar_balance,
        )
        logger.info("Generated %d suggestions", len(suggestions))

    except Exception as e:
        logger.error("Suggestion generation failed: %s", e)
        try:
            sheets.log_error("suggest", str(e))
        except Exception:
            logger.exception("Failed to log error to Sheet")
        result.errors += 1
        return result

    # Write suggestions to Sheet
    for suggestion in suggestions:
        try:
            sheets.add_suggestion(suggestion)
            result.processed += 1
            logger.info("Added suggestion: %s", suggestion.content_idea[:50])
        except Exception as e:
            logger.error("Failed to write suggestion: %s", e)
            result.errors += 1

    logger.info(
        "Suggest pipeline complete: %d written, %d errors",
        result.processed,
        result.errors,
    )
    return result


def learn_pipeline(
    *,
    sheets: SheetsClient,
    postiz: PostizClient,
    intelligence: ContentIntelligence,
    data_dir: Path = Path("data"),
) -> PipelineResult:
    """Run the Learning Pipeline.

    Pulls engagement data from Postiz for posted content,
    merges into post-performance.json, and updates the
    learning context used by AI caption generation.
    """
    result = PipelineResult()
    perf_path = data_dir / "post-performance.json"

    # Load existing performance data
    existing: list[dict] = []
    if perf_path.exists():
        existing = json.loads(perf_path.read_text())
    existing_ids = {p["post_id"] for p in existing}

    # Get posted rows from Sheet
    posted_rows = sheets.get_rows_by_status(ContentStatus.POSTED)
    logger.info("Found %d posted rows to pull analytics for", len(posted_rows))

    new_posts: list[dict] = []
    for row in posted_rows:
        if not row.postiz_ids:
            result.skipped += 1
            continue

        pillar = row.content_pillar or ContentPillar.COW_LIFE

        for post_id in row.postiz_ids.split(","):
            post_id = post_id.strip()
            if not post_id:
                continue

            if post_id in existing_ids:
                result.skipped += 1
                continue

            try:
                perf = postiz.get_post_analytics(post_id, pillar)
                new_posts.append(perf.model_dump(mode="json"))
                existing_ids.add(post_id)
                result.processed += 1
                logger.info("Pulled analytics for %s", post_id)
            except Exception as e:
                logger.warning("Failed to get analytics for %s: %s", post_id, e)
                result.errors += 1

    # Save merged performance data
    if new_posts:
        existing.extend(new_posts)
        data_dir.mkdir(parents=True, exist_ok=True)
        perf_path.write_text(json.dumps(existing, indent=2))
        logger.info("Saved %d new post records (%d total)", len(new_posts), len(existing))

    # Update learning context
    intelligence.save_learning_context()

    logger.info(
        "Learn pipeline complete: %d new, %d skipped, %d errors",
        result.processed,
        result.skipped,
        result.errors,
    )
    return result
