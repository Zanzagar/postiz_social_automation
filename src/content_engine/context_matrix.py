"""Context injection matrix for consistent prompt context.

Defines which context types are injected into which endpoint,
preventing accidental knowledge shoehorning in iterate prompts
or missing festivals in calendar prompts.
"""

from typing import Any

# What context each endpoint receives
CONTEXT_MATRIX: dict[str, list[str]] = {
    "generate": ["brand_voice", "learned_rules", "knowledge", "few_shots"],
    "iterate": ["brand_voice", "learned_rules", "few_shots"],
    "reprompt": [
        "brand_voice",
        "learned_rules",
        "knowledge",
        "few_shots",
    ],
    "calendar": [
        "brand_voice",
        "learned_rules",
        "knowledge",
        "festivals",
    ],
    "suggest": [
        "brand_voice",
        "learned_rules",
        "knowledge",
        "festivals",
    ],
    "classify": ["brand_voice"],
}

# Fallback for unknown endpoints
_DEFAULT_CONTEXT = ["brand_voice"]


def build_context(endpoint: str, **kwargs: Any) -> dict[str, Any]:
    """Build a context dict containing only the items needed.

    Args:
        endpoint: One of generate, iterate, reprompt, calendar, suggest.
        **kwargs: All available context items (brand_voice, knowledge, etc.)

    Returns:
        Dict with only the context items allowed for this endpoint,
        excluding None values.
    """
    allowed = CONTEXT_MATRIX.get(endpoint, _DEFAULT_CONTEXT)
    return {key: value for key, value in kwargs.items() if key in allowed and value is not None}
