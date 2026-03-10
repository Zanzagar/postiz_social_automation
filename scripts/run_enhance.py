#!/usr/bin/env python3
"""Mode 1: Enhance Pipeline — process 'ready' rows from Google Sheets.

Usage:
    python scripts/run_enhance.py

Requires environment variables (or .env file):
    GOOGLE_CREDENTIALS_PATH  — path to service account JSON
    SPREADSHEET_ID           — Google Sheets ID for the content calendar
    POSTIZ_API_KEY           — Postiz API key
"""

import logging
import os
import sys

from dotenv import load_dotenv

from content_engine.generator import CaptionGenerator
from content_engine.pipeline import enhance_pipeline
from content_engine.postiz import PostizClient
from content_engine.sheets import SheetsClient
from content_engine.validator import ContentValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Run the enhance pipeline with configured clients."""
    load_dotenv()

    required_vars = ["GOOGLE_CREDENTIALS_PATH", "SPREADSHEET_ID", "POSTIZ_API_KEY"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return 1

    sheets = SheetsClient(
        credentials_path=os.environ["GOOGLE_CREDENTIALS_PATH"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
    )
    postiz = PostizClient(api_key=os.environ["POSTIZ_API_KEY"])
    generator = CaptionGenerator()
    validator = ContentValidator()

    result = enhance_pipeline(
        sheets=sheets,
        postiz=postiz,
        generator=generator,
        validator=validator,
    )

    logger.info(
        "Done: %d processed, %d errors, %d skipped",
        result.processed,
        result.errors,
        result.skipped,
    )
    return 1 if result.errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
