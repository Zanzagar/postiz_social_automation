"""Model configuration per task type.

Allows different Claude models for different task types, configurable via
environment variables (e.g. CLAUDE_MODEL_GENERATE=opus).
"""

import os

DEFAULT_MODELS: dict[str, str] = {
    "generate": "sonnet",
    "iterate": "sonnet",
    "suggest": "sonnet",
    "calendar": "sonnet",
    "classify": "haiku",
}

_FALLBACK_MODEL = "sonnet"


def get_model(task_type: str) -> str:
    """Return the Claude model name for a given task type.

    Checks for an environment variable override first
    (e.g. CLAUDE_MODEL_GENERATE), then falls back to the default mapping.
    Unknown task types return 'sonnet'.
    """
    env_key = f"CLAUDE_MODEL_{task_type.upper()}"
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val

    return DEFAULT_MODELS.get(task_type, _FALLBACK_MODEL)
