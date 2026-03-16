"""FastAPI dependency injection for shared clients."""

from functools import lru_cache

from api.config import Settings
from content_engine.generator import CaptionGenerator
from content_engine.postiz import PostizClient


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_postiz_client(settings: Settings | None = None) -> PostizClient:
    """Build a PostizClient from settings."""
    if settings is None:
        settings = get_settings()
    return PostizClient(
        api_key=settings.postiz_api_key,
        base_url=settings.postiz_base_url,
    )


def get_caption_generator() -> CaptionGenerator:
    """Build a CaptionGenerator with default data dir."""
    return CaptionGenerator()
