"""FastAPI dependency injection for shared clients."""

from functools import lru_cache

from api.config import Settings
from content_engine.generator import CaptionGenerator
from content_engine.postiz import PostizClient
from content_engine.sheets import SheetsClient


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_postiz_client() -> PostizClient:
    """Build a PostizClient from settings."""
    settings = get_settings()
    return PostizClient(
        api_key=settings.postiz_api_key,
        base_url=settings.postiz_base_url,
    )


def get_sheets_client() -> SheetsClient:
    """Build a SheetsClient from settings."""
    settings = get_settings()
    return SheetsClient(
        credentials_path=settings.google_sheets_credentials,
        spreadsheet_id=settings.spreadsheet_id,
    )


def get_caption_generator() -> CaptionGenerator:
    """Build a CaptionGenerator with default data dir."""
    return CaptionGenerator()
