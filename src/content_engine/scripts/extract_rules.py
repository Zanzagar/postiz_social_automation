"""Extract learned voice rules from content iteration history.

Analyzes old_caption → new_caption diffs and user instructions from
content_iterations to produce generalizable rules for future prompts.

Usage:
    python -m content_engine.scripts.extract_rules
    python -m content_engine.scripts.extract_rules --dry-run
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
RULES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "learned-rules.json"
CLI_TIMEOUT = 120


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


def main():
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT refinement_instruction, old_caption, new_caption, platform
        FROM content_iterations
        WHERE old_caption IS NOT NULL AND new_caption IS NOT NULL
        AND old_caption != new_caption
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()

    if len(rows) < 3:
        logger.info("Only %d iterations — need at least 3 to extract patterns", len(rows))
        return

    logger.info("Analyzing %d iterations for patterns...", len(rows))

    # Load existing rules to preserve/update them
    existing_rules = []
    if RULES_PATH.exists():
        existing_rules = json.loads(RULES_PATH.read_text()).get("rules", [])
        logger.info("Loaded %d existing rules", len(existing_rules))

    # Build the iteration examples
    examples = []
    for r in rows[:20]:  # Cap at 20 most recent
        examples.append(
            f'Instruction: "{r["refinement_instruction"]}"\n'
            f"Before ({r['platform']}): {(r['old_caption'] or '')[:200]}\n"
            f"After ({r['platform']}): {(r['new_caption'] or '')[:200]}"
        )

    existing_block = ""
    if existing_rules:
        existing_block = (
            "\nEXISTING RULES (update, merge, or remove as needed):\n"
            + "\n".join(f"- {r}" for r in existing_rules)
            + "\n"
        )

    prompt = f"""Analyze these content editing sessions from a social media manager.
Each shows what they asked for, what the AI produced before, and what they accepted after.

EDITING SESSIONS:
{"---".join(examples)}
{existing_block}
Extract generalizable rules about this editor's preferences. Focus on:
- What kinds of changes do they consistently make?
- What patterns appear across multiple edits?
- What do they add or remove?
- What tone/length/style do they prefer?

Return a JSON object with:
- "rules": array of strings, each a specific, actionable rule (max 15 rules)
- "summary": one sentence summarizing the editor's overall preference

Rules should be specific enough to act on ("keep posts under 80 words")
not vague ("write better content"). Only include rules supported by
multiple iterations. Remove rules that contradict the evidence.

Return ONLY valid JSON, no markdown fences."""

    raw = _call_claude(prompt)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    result = json.loads(raw)
    rules = result.get("rules", [])
    summary = result.get("summary", "")

    logger.info("Extracted %d rules", len(rules))
    logger.info("Summary: %s", summary)
    for i, rule in enumerate(rules, 1):
        logger.info("  %d. %s", i, rule)

    if not dry_run:
        RULES_PATH.write_text(json.dumps(result, indent=2))
        logger.info("Saved to %s", RULES_PATH)
    else:
        logger.info("(dry run — not saved)")


if __name__ == "__main__":
    main()
