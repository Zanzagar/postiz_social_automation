"""FastAPI dependency injection for shared clients."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import Settings
from api.repositories.content import ContentRepository
from content_engine.generator import CaptionGenerator
from content_engine.postiz import PostizClient
from content_engine.sheets import SheetsClient

_engine = None
_session_factory = None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_session_factory() -> async_sessionmaker:
    """Return the shared async session factory, creating it on first use."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(f"sqlite+aiosqlite:///{settings.database_path}")
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def get_content_repo(session: AsyncSession = Depends(get_db)) -> ContentRepository:
    """Build a ContentRepository from the current database session."""
    return ContentRepository(session)


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
    """Build a CaptionGenerator.

    Always uses the real CaptionGenerator (Claude CLI via OAuth) even in
    demo mode — AI generation is free via Max subscription and should
    work everywhere Claude CLI is available.
    """
    return CaptionGenerator()
