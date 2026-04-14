"""Regex-based slop detection for AI-generated content.

Catches common AI cliches, Gita Valley-specific anti-patterns,
and filler phrases using ~80 compiled regex patterns. Scoring
is additive with category-based weights, capped at 1.0.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_PATTERNS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "slop_patterns.json"
)

# Weight per category (how much each match adds to the score)
CATEGORY_WEIGHTS = {
    "ai_cliches": 0.15,
    "gita_valley_antipatterns": 0.20,
    "filler_phrases": 0.10,
}

DEFAULT_THRESHOLD = 0.3


@dataclass
class SlopResult:
    """Result of slop detection on a piece of text."""

    score: float
    matches: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def is_slop(self, threshold: float = DEFAULT_THRESHOLD) -> bool:
        return self.score >= threshold


@dataclass
class _CompiledPattern:
    regex: re.Pattern
    category: str
    raw: str


class SlopDetector:
    """Detect AI-generated cliches and anti-patterns in text."""

    def __init__(self, patterns_path: Path | str | None = None) -> None:
        path = Path(patterns_path) if patterns_path else _DEFAULT_PATTERNS_PATH
        self.patterns: list[_CompiledPattern] = []
        self._load_patterns(path)

    def _load_patterns(self, path: Path) -> None:
        """Load and compile regex patterns from JSON file."""
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for category, pattern_list in data.items():
            for raw in pattern_list:
                try:
                    compiled = re.compile(raw, re.IGNORECASE)
                    self.patterns.append(
                        _CompiledPattern(
                            regex=compiled,
                            category=category,
                            raw=raw,
                        )
                    )
                except re.error:
                    pass  # Skip invalid regex

    def detect(self, text: str) -> SlopResult:
        """Scan text for slop patterns and return scored result."""
        if not text:
            return SlopResult(score=0.0)

        matches: list[str] = []
        score = 0.0

        for pattern in self.patterns:
            if pattern.regex.search(text):
                weight = CATEGORY_WEIGHTS.get(pattern.category, 0.1)
                score += weight
                # Use the actual match text for the report
                m = pattern.regex.search(text)
                matched_text = m.group(0) if m else pattern.raw
                matches.append(matched_text)

        return SlopResult(
            score=min(score, 1.0),
            matches=matches,
        )
