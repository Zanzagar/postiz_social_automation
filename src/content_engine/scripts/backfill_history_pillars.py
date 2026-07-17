"""Backfill NULL pillars on social_history rows via Claude classification.

Classifies each unclassified history post into one of the ACTIVE pillars
(fetched dynamically from the pillars table — never hardcoded) using the
Claude CLI. Posts are batched (up to 10 per call, strict JSON response)
to conserve calls; up to 3 CLI calls run concurrently. Unclassifiable
posts are left NULL.

Usage:
    python -m content_engine.scripts.backfill_history_pillars [--limit N] [--dry-run]
"""

import argparse
import json
import logging
import os
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 10  # posts per Claude call — batched to conserve calls
CLI_TIMEOUT = 120  # seconds
MAX_CONCURRENT = 3  # concurrent Claude CLI calls
TEXT_SNIPPET_LEN = 300  # chars of post text sent per item

# Run claude -p from /tmp so it doesn't load the project's .claude/ directory
# (rules, hooks, plugins) which adds 40s+ of startup.
_CLEAN_CWD = "/tmp"


def get_db_path() -> str:
    return os.environ.get("DATABASE_PATH", "data/gvsa.db")


def fetch_active_pillars(conn: sqlite3.Connection) -> list[str]:
    """ACTIVE pillar names from the DB, in display order. Never hardcoded."""
    rows = conn.execute(
        "SELECT name FROM pillars WHERE is_active = 1 ORDER BY sort_order, name"
    ).fetchall()
    return [r[0] for r in rows]


def fetch_unclassified(conn: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    """social_history rows with NULL pillar and enough text to classify."""
    sql = (
        "SELECT id, post_text FROM social_history"
        " WHERE pillar IS NULL AND post_text IS NOT NULL AND length(post_text) > 10"
        " ORDER BY id"
    )
    params: tuple = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    return [{"id": r[0], "text": r[1]} for r in conn.execute(sql, params).fetchall()]


def _call_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "sonnet"],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
        stdin=subprocess.DEVNULL,
        cwd=_CLEAN_CWD,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {result.stderr[:200]}")
    return result.stdout.strip()


def build_prompt(batch: list[dict], pillars: list[str]) -> str:
    pillar_lines = "\n".join(f"- {p}" for p in pillars)
    items = "\n".join(
        f"[{e['id']}] {' '.join((e['text'] or '').split())[:TEXT_SNIPPET_LEN]}" for e in batch
    )
    return f"""Classify each social media post into exactly one content pillar.

PILLARS (use these exact names):
{pillar_lines}

POSTS:
{items}

Return ONLY a JSON array: [{{"id": <post id>, "pillar": "<pillar name>"}}].
Omit posts that don't clearly fit any pillar. Pillar names must match the
list above exactly. No markdown fences. No explanation."""


def classify_batch(batch: list[dict], pillars: list[str]) -> dict[int, str]:
    """Classify one batch via Claude. Returns {row_id: pillar_name}."""
    raw = _call_claude(build_prompt(batch, pillars))
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    out: dict[int, str] = {}
    for item in json.loads(raw):
        try:
            out[int(item["id"])] = str(item["pillar"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Backfill NULL pillars on social_history rows via Claude."
    )
    parser.add_argument("--limit", type=int, default=None, help="Max rows to classify")
    parser.add_argument(
        "--dry-run", action="store_true", help="Log classifications without writing"
    )
    args = parser.parse_args(argv)

    conn = sqlite3.connect(get_db_path())
    try:
        pillars = fetch_active_pillars(conn)
        if not pillars:
            logger.error("No active pillars in the database — nothing to classify against")
            return
        rows = fetch_unclassified(conn, args.limit)
        logger.info("Active pillars: %s", ", ".join(pillars))
        logger.info("Found %d social_history rows with NULL pillar", len(rows))
        if not rows:
            logger.info("Nothing to classify")
            return

        batches = [rows[i : i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
        valid_names = set(pillars)
        classified = 0
        invalid = 0
        failed_batches = 0
        done = 0

        # CLI calls run in threads (max 3 concurrent); all DB writes stay on
        # the main thread — sqlite connections are not shared across threads.
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
            futures = {pool.submit(classify_batch, batch, pillars): batch for batch in batches}
            for future in as_completed(futures):
                batch = futures[future]
                done += 1
                try:
                    result = future.result()
                except Exception as e:
                    failed_batches += 1
                    logger.error("Batch failed (%d posts left NULL): %s", len(batch), e)
                    continue

                batch_ids = {e["id"] for e in batch}
                for row_id, pillar in result.items():
                    if row_id not in batch_ids:
                        continue
                    if pillar not in valid_names:
                        invalid += 1
                        logger.warning("Row %d: invalid pillar %r — left NULL", row_id, pillar)
                        continue
                    if args.dry_run:
                        logger.info("[dry-run] row %d -> %s", row_id, pillar)
                    else:
                        conn.execute(
                            "UPDATE social_history SET pillar = ? WHERE id = ?",
                            (pillar, row_id),
                        )
                    classified += 1
                if not args.dry_run:
                    conn.commit()
                logger.info("Progress: %d/%d batches", done, len(batches))

        logger.info(
            "Done. Classified: %d/%d rows%s. Invalid pillar names: %d. Failed batches: %d.",
            classified,
            len(rows),
            " (dry-run — nothing written)" if args.dry_run else "",
            invalid,
            failed_batches,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
