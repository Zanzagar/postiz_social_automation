"""Mode 2: Suggest — AI-proactive content generation from calendar/events.

Usage:
    python -m content_engine.scripts.run_suggest
    suggest  # via pyproject.toml entry point
"""

import logging
import os
import sys

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for the suggest pipeline."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Validate required env vars
    required = ["GOOGLE_SHEETS_CREDENTIALS", "SPREADSHEET_ID", "POSTIZ_API_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error("Missing environment variables: %s", ", ".join(missing))
        sys.exit(1)

    from content_engine.generator import CaptionGenerator
    from content_engine.intelligence import ContentIntelligence
    from content_engine.pipeline import suggest_pipeline
    from content_engine.postiz import PostizClient
    from content_engine.sheets import SheetsClient

    sheets = SheetsClient(
        credentials_path=os.environ["GOOGLE_SHEETS_CREDENTIALS"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
    )
    postiz = PostizClient(
        api_key=os.environ["POSTIZ_API_KEY"],
        base_url=os.getenv("POSTIZ_BASE_URL", "https://postiz.sethpc.xyz/api/public/v1"),
    )
    generator = CaptionGenerator()
    intelligence = ContentIntelligence(sheets=sheets, postiz=postiz)

    result = suggest_pipeline(
        sheets=sheets,
        postiz=postiz,
        generator=generator,
        intelligence=intelligence,
    )

    logger.info("Done: %d suggestions written, %d errors", result.processed, result.errors)
    sys.exit(1 if result.errors > 0 else 0)


if __name__ == "__main__":
    main()
