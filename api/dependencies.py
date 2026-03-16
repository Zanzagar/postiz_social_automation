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


def get_postiz_client():
    """Build a PostizClient from settings (or demo mock)."""
    settings = get_settings()
    if settings.demo_mode:
        from api.demo import DemoPostizClient

        return DemoPostizClient()
    return PostizClient(
        api_key=settings.postiz_api_key,
        base_url=settings.postiz_base_url,
    )


def get_sheets_client():
    """Build a SheetsClient from settings (or demo mock)."""
    settings = get_settings()
    if settings.demo_mode:
        from api.demo import DemoSheetsClient

        return DemoSheetsClient()
    return SheetsClient(
        credentials_path=settings.google_sheets_credentials,
        spreadsheet_id=settings.spreadsheet_id,
    )


def get_caption_generator():
    """Build a CaptionGenerator (or demo mock)."""
    settings = get_settings()
    if settings.demo_mode:
        from api.demo import DemoCaptionGenerator

        return DemoCaptionGenerator()
    return CaptionGenerator()
