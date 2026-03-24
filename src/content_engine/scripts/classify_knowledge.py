"""Classify web_knowledge entries by content pillar.

One-time migration script. Sends batches of entries to Claude for
pillar classification, then updates the database.

Usage:
    python -m content_engine.scripts.classify_knowledge
    python -m content_engine.scripts.classify_knowledge --dry-run
"""

import json
import logging
import sqlite3
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "gvsa.db"
BATCH_SIZE = 100
CLI_TIMEOUT = 120

PILLARS = [
    "Spiritual Education",
    "Farm & Community",
    "Events",
    "Behind the Scenes",
    "Seasonal",
    "Collaborative",
]


def _call_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "opus", "--effort", "max"],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
        stdin=subprocess.DEVNULL,
        cwd="/tmp",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude failed: {result.stderr[:200]}")
    return result.stdout.strip()


def classify_batch(entries: list[dict]) -> dict[int, str]:
    """Send a batch of entries to Claude for classification. Returns {id: pillar}."""
    items = "\n".join(f"[{e['id']}] ({e['fact_type']}) {e['content'][:150]}" for e in entries)

    prompt = f"""Classify each knowledge base entry into exactly one pillar.

PILLARS:
- Spiritual Education: scripture, philosophy, devotion, mantras, spiritual practice, Krishna consciousness
- Farm & Community: cows, dairy, farming, agriculture, CSA, volunteers, team, daily operations
- Events: festivals, retreats, programs, workshops, celebrations, commemorations
- Behind the Scenes: staff stories, cow personalities, day-to-day life, infrastructure
- Seasonal: weather, seasons, seasonal activities, holiday-related
- Collaborative: partnerships, donations, fundraising, outreach, education programs

ENTRIES:
{items}

Return ONLY a JSON object mapping entry ID (as string) to pillar name.
Example: {{"123": "Farm & Community", "456": "Events"}}
No markdown fences. No explanation."""

    raw = _call_claude(prompt)
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return {int(k): v for k, v in json.loads(raw).items()}


def main():
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get unclassified entries
    rows = conn.execute(
        """SELECT id, fact_type, content FROM web_knowledge
           WHERE pillar IS NULL
           AND content IS NOT NULL AND length(content) > 10
           ORDER BY id"""
    ).fetchall()

    logger.info("Found %d unclassified entries", len(rows))
    if not rows:
        logger.info("Nothing to classify")
        return

    entries = [{"id": r["id"], "fact_type": r["fact_type"], "content": r["content"]} for r in rows]
    total_updated = 0

    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(entries) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Batch %d/%d (%d entries)...", batch_num, total_batches, len(batch))

        try:
            classifications = classify_batch(batch)
        except Exception as e:
            logger.error("Batch %d failed: %s", batch_num, e)
            continue

        valid = {k: v for k, v in classifications.items() if v in PILLARS}
        invalid = {k: v for k, v in classifications.items() if v not in PILLARS}
        if invalid:
            logger.warning("Skipping %d entries with invalid pillar: %s", len(invalid), invalid)

        if dry_run:
            for entry_id, pillar in valid.items():
                content = next((e["content"][:60] for e in batch if e["id"] == entry_id), "?")
                logger.info("  [%d] %s -> %s", entry_id, content, pillar)
        else:
            for entry_id, pillar in valid.items():
                conn.execute(
                    "UPDATE web_knowledge SET pillar = ? WHERE id = ?",
                    (pillar, entry_id),
                )
            conn.commit()

        total_updated += len(valid)
        logger.info("  Classified %d/%d in batch", len(valid), len(batch))

    logger.info("Done. Total classified: %d/%d", total_updated, len(entries))
    conn.close()


if __name__ == "__main__":
    main()
