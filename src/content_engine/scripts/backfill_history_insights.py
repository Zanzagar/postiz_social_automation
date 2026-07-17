"""Backfill reach (and impressions when the column exists) on social_history.

For rows with reach == 0, fetches per-post insights from the Meta Graph API
(GET /{post_id}/insights?metric=post_impressions,post_impressions_unique)
and writes reach = post_impressions_unique. The impressions value is only
stored when the social_history table actually has an impressions column
(checked at runtime — the live schema does not have one, so reach only).

Graceful exits: missing META_PAGE_ACCESS_TOKEN → clear message, no HTTP;
per-post API errors → row skipped and counted.

Usage:
    python -m content_engine.scripts.backfill_history_insights [--dry-run]
"""

import argparse
import logging
import os
import sqlite3

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
METRICS = "post_impressions,post_impressions_unique"
HTTP_TIMEOUT = 30  # seconds
COMMIT_EVERY = 25  # rows


def get_db_path() -> str:
    return os.environ.get("DATABASE_PATH", "data/gvsa.db")


def has_impressions_column(conn: sqlite3.Connection) -> bool:
    """Check the live schema — the model has no impressions column today."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(social_history)")]
    return "impressions" in cols


def fetch_post_insights(post_id: str, access_token: str) -> dict[str, int]:
    """Fetch {metric_name: value} for one post. Raises on API errors."""
    url = f"{GRAPH_API_BASE}/{post_id}/insights"
    resp = httpx.get(
        url,
        params={"metric": METRICS, "access_token": access_token},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    out: dict[str, int] = {}
    for entry in resp.json().get("data", []):
        values = entry.get("values") or []
        if values and entry.get("name"):
            out[entry["name"]] = int(values[0].get("value") or 0)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Backfill reach/impressions on social_history rows via the Graph API."
    )
    parser.add_argument("--dry-run", action="store_true", help="Log updates without writing")
    args = parser.parse_args(argv)

    access_token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not access_token:
        logger.error("META_PAGE_ACCESS_TOKEN env var required — set it and re-run")
        return

    conn = sqlite3.connect(get_db_path())
    try:
        write_impressions = has_impressions_column(conn)
        if write_impressions:
            logger.info("impressions column found — storing reach and impressions")
        else:
            logger.info("No impressions column on social_history — storing reach only")

        rows = conn.execute(
            "SELECT id, external_id FROM social_history WHERE reach = 0 ORDER BY id"
        ).fetchall()
        logger.info("Found %d rows with reach == 0", len(rows))
        if not rows:
            logger.info("Nothing to backfill")
            return

        updated = 0
        skipped = 0
        for i, (row_id, external_id) in enumerate(rows, start=1):
            try:
                insights = fetch_post_insights(external_id, access_token)
            except Exception as e:
                skipped += 1
                logger.warning(
                    "Row %d (%s): insights fetch failed — skipped (%s)", row_id, external_id, e
                )
                continue

            reach = insights.get("post_impressions_unique")
            impressions = insights.get("post_impressions")
            if reach is None:
                skipped += 1
                logger.warning(
                    "Row %d (%s): no post_impressions_unique in response — skipped",
                    row_id,
                    external_id,
                )
                continue

            if args.dry_run:
                extra = (
                    f", impressions={impressions}"
                    if write_impressions and impressions is not None
                    else ""
                )
                logger.info("[dry-run] row %d -> reach=%d%s", row_id, reach, extra)
            elif write_impressions and impressions is not None:
                conn.execute(
                    "UPDATE social_history SET reach = ?, impressions = ? WHERE id = ?",
                    (reach, impressions, row_id),
                )
            else:
                conn.execute("UPDATE social_history SET reach = ? WHERE id = ?", (reach, row_id))
            updated += 1

            if i % COMMIT_EVERY == 0:
                if not args.dry_run:
                    conn.commit()
                logger.info("Progress: %d/%d rows", i, len(rows))

        if not args.dry_run:
            conn.commit()
        logger.info(
            "Done. Updated: %d, Skipped (errors): %d%s",
            updated,
            skipped,
            " (dry-run — nothing written)" if args.dry_run else "",
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
