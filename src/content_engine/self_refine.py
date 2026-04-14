"""Self-refine scoring loop for caption quality assessment.

Uses Claude Haiku to score captions on voice match, platform fit,
specificity, and slop-free quality. Triggers refinement when
overall score falls below threshold.
"""

import json
import logging
import os
import re
from dataclasses import dataclass

from content_engine.generator import _call_claude
from content_engine.prompt_builder import PLATFORM_CONSTRAINTS

logger = logging.getLogger(__name__)

REFINEMENT_THRESHOLD = 7.0
SELF_REFINE_ENABLED = os.environ.get("SELF_REFINE_ENABLED", "true").lower() != "false"


@dataclass
class QualityScore:
    """Quality assessment of a generated caption."""

    voice_match: int  # 1-10
    platform_fit: int  # 1-10
    specificity: int  # 1-10
    slop_free: int  # 1-10
    feedback: str

    @property
    def overall(self) -> float:
        return (self.voice_match + self.platform_fit + self.specificity + self.slop_free) / 4.0

    def needs_refinement(self, threshold: float = REFINEMENT_THRESHOLD) -> bool:
        return self.overall < threshold


def score_caption(
    caption: str,
    platform: str,
    voice_profile: dict | None = None,
) -> QualityScore:
    """Score a caption using Claude Haiku for quality assessment."""
    constraints = PLATFORM_CONSTRAINTS.get(platform.lower(), "")

    prompt = (
        "Score this social media caption on four dimensions (1-10 each).\n\n"
        f"Caption: {caption}\n"
        f"Platform: {platform}\n"
        f"Platform rules: {constraints}\n\n"
        "Scoring rubric:\n"
        "- voice_match: Does it sound like a real farmer, not AI?\n"
        "- platform_fit: Does it follow platform-specific rules?\n"
        "- specificity: Does it use concrete details, not generics?\n"
        "- slop_free: Is it free of AI cliches and filler?\n\n"
        "Return ONLY a JSON object with keys: voice_match, platform_fit, "
        "specificity, slop_free (integers 1-10), feedback (string)."
    )

    try:
        raw = _call_claude(prompt, model="haiku")
        data = _parse_score(raw)
        if data:
            return QualityScore(
                voice_match=int(data.get("voice_match", 5)),
                platform_fit=int(data.get("platform_fit", 5)),
                specificity=int(data.get("specificity", 5)),
                slop_free=int(data.get("slop_free", 5)),
                feedback=data.get("feedback", ""),
            )
    except Exception as e:
        logger.warning("Score caption failed: %s", e)

    # Default low score on failure
    return QualityScore(
        voice_match=5,
        platform_fit=5,
        specificity=5,
        slop_free=5,
        feedback="Scoring failed — defaulting to conservative score",
    )


def _parse_score(raw: str) -> dict | None:
    """Parse JSON score from Claude response."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "voice_match" in data:
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
