"""Two-stage content generation pipeline.

Stage 1: Generate a core narrative (message, details, hook, CTA)
         from raw text + knowledge context using Sonnet.
Stage 2: Adapt the narrative to each platform (separate module).
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from content_engine.generator import _call_claude
from content_engine.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class CoreNarrative:
    """The distilled core of a post, before platform adaptation."""

    core_message: str
    key_details: list[str]
    emotional_hook: str
    cta: str


class TwoStageGenerator:
    """Two-stage content generation: narrative extraction → platform adapt."""

    def __init__(self, data_dir: Path = _DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir
        self.prompt_builder = PromptBuilder(
            voice_profile=self._load_json("voice-profile.json"),
            learned_rules=self._load_json("learned-rules.json").get("rules", []),
        )

    def _load_json(self, filename: str) -> dict:
        path = self.data_dir / filename
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def generate_core_narrative(
        self,
        raw_text: str,
        pillar: str,
        knowledge_context: str | None = None,
    ) -> CoreNarrative:
        """Stage 1: Extract core narrative from raw text.

        Uses Sonnet to distill the post into structured components.
        Retries once with a simpler prompt on parse failure.
        """
        prompt = self._build_narrative_prompt(raw_text, pillar, knowledge_context)
        raw = _call_claude(prompt)

        data = self._parse_narrative(raw)
        if data is not None:
            return self._dict_to_narrative(data)

        # Retry with simpler prompt
        logger.warning("Narrative parse failed, retrying with simpler prompt")
        simple_prompt = (
            f"Extract the core narrative from this social media post idea.\n\n"
            f"Post: {raw_text}\nPillar: {pillar}\n\n"
            f"Return ONLY a JSON object with these keys:\n"
            f"core_message (1 sentence), key_details (list of strings), "
            f"emotional_hook (the feeling), cta (call to action)\n\n"
            f"JSON only, no other text."
        )
        raw2 = _call_claude(simple_prompt)
        data2 = self._parse_narrative(raw2)
        if data2 is not None:
            return self._dict_to_narrative(data2)

        raise RuntimeError(f"Could not parse core narrative after retry: {raw2[:200]}")

    def _build_narrative_prompt(
        self,
        raw_text: str,
        pillar: str,
        knowledge_context: str | None,
    ) -> str:
        """Build XML prompt for Stage 1 narrative extraction."""
        sections = [
            self.prompt_builder._wrap_xml(
                "system",
                "You are a content strategist for Gita Valley farm. "
                "Extract the core narrative from a post idea — distill it "
                "into a structured form that can be adapted to any platform.",
            ),
        ]

        voice = self.prompt_builder._voice_section()
        if voice:
            sections.append(voice)

        if knowledge_context:
            sections.append(self.prompt_builder._wrap_xml("knowledge", knowledge_context))

        sections.append(
            self.prompt_builder._wrap_xml(
                "content",
                f"Raw post idea: {self.prompt_builder._escape(raw_text)}\nContent pillar: {pillar}",
            )
        )

        sections.append(
            self.prompt_builder._wrap_xml(
                "output_format",
                "Return ONLY a JSON object with these keys:\n"
                '- "core_message": The main point in 1 sentence\n'
                '- "key_details": List of specific facts to include\n'
                '- "emotional_hook": The feeling to evoke\n'
                '- "cta": Call to action\n\n'
                "No other text, just the JSON object.",
            )
        )

        return "\n\n".join(sections)

    @staticmethod
    def _parse_narrative(raw: str) -> dict | None:
        """Parse JSON from Claude response, handling common formats."""
        text = raw.strip()

        # Strip markdown fences
        fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if fence:
            text = fence.group(1).strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "core_message" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from mixed text
        match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and "core_message" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _dict_to_narrative(data: dict) -> CoreNarrative:
        return CoreNarrative(
            core_message=data.get("core_message", ""),
            key_details=data.get("key_details", []),
            emotional_hook=data.get("emotional_hook", ""),
            cta=data.get("cta", ""),
        )
