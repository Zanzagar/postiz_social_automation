"""Learning Pipeline — pull engagement data and update learning context.

Usage:
    python -m content_engine.scripts.run_learn
    learn  # via pyproject.toml entry point
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for the learning pipeline."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    required = ["GOOGLE_SHEETS_CREDENTIALS", "SPREADSHEET_ID", "POSTIZ_API_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error("Missing environment variables: %s", ", ".join(missing))
        sys.exit(1)

    from content_engine.intelligence import ContentIntelligence
    from content_engine.pipeline import learn_pipeline
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
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    intelligence = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=data_dir)

    result = learn_pipeline(
        sheets=sheets,
        postiz=postiz,
        intelligence=intelligence,
        data_dir=data_dir,
    )

    logger.info(
        "Done: %d new records, %d skipped, %d errors",
        result.processed,
        result.skipped,
        result.errors,
    )
    sys.exit(1 if result.errors > 0 else 0)


if __name__ == "__main__":
    main()
