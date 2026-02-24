"""Mode 1: Enhance — take staff input and generate platform-ready posts.

Usage:
    python -m content_engine.scripts.run_enhance
    enhance  # via pyproject.toml entry point
"""

import logging
import os
import sys

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for the enhance pipeline."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    required = ["GOOGLE_SHEETS_CREDENTIALS", "SPREADSHEET_ID"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error("Missing environment variables: %s", ", ".join(missing))
        sys.exit(1)

    from content_engine.generator import CaptionGenerator
    from content_engine.pipeline import enhance_pipeline
    from content_engine.postiz import PostizClient
    from content_engine.sheets import SheetsClient
    from content_engine.validator import ContentValidator

    sheets = SheetsClient(
        credentials_path=os.environ["GOOGLE_SHEETS_CREDENTIALS"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
    )

    postiz_api_key = os.getenv("POSTIZ_API_KEY")
    postiz = (
        PostizClient(
            api_key=postiz_api_key or "",
            base_url=os.getenv("POSTIZ_BASE_URL", "https://postiz.sethpc.xyz/api/public/v1"),
        )
        if postiz_api_key
        else None
    )

    data_dir_str = os.getenv("DATA_DIR", "data")
    from pathlib import Path

    data_dir = Path(data_dir_str)

    generator = CaptionGenerator(data_dir=data_dir)
    validator = ContentValidator()

    if postiz is None:
        logger.error("POSTIZ_API_KEY not set — cannot create drafts")
        sys.exit(1)

    result = enhance_pipeline(
        sheets=sheets,
        postiz=postiz,
        generator=generator,
        validator=validator,
    )

    logger.info(
        "Done: %d processed, %d skipped, %d errors",
        result.processed,
        result.skipped,
        result.errors,
    )
    sys.exit(1 if result.errors > 0 else 0)


if __name__ == "__main__":
    main()
