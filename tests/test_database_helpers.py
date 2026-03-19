"""Tests for database connection helpers and seed data (Phase 1 — Task #1, subtask 1.5)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.database import get_async_engine, seed_starter_templates
from api.models import Base, Template


@pytest.fixture
def sync_engine():
    """In-memory sync engine for seed tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def sync_session(sync_engine):
    with Session(sync_engine) as session:
        yield session


class TestSeedStarterTemplates:
    def test_seeds_four_templates(self, sync_session):
        seed_starter_templates(sync_session)
        templates = sync_session.query(Template).all()
        assert len(templates) == 4

    def test_seed_template_names(self, sync_session):
        seed_starter_templates(sync_session)
        names = {t.name for t in sync_session.query(Template).all()}
        assert names == {
            "Sunday Feast",
            "Weekly Verse",
            "Farm Update",
            "Event Promotion",
        }

    def test_seed_template_has_variables(self, sync_session):
        seed_starter_templates(sync_session)
        feast = sync_session.query(Template).filter_by(name="Sunday Feast").one()
        variables = json.loads(feast.variables)
        assert len(variables) > 0
        assert any(v["name"] == "menu" for v in variables)

    def test_seed_template_has_schedule_pattern(self, sync_session):
        seed_starter_templates(sync_session)
        feast = sync_session.query(Template).filter_by(name="Sunday Feast").one()
        assert feast.schedule_pattern == "weekly:sunday"

    def test_seed_template_has_pillar(self, sync_session):
        seed_starter_templates(sync_session)
        verse = sync_session.query(Template).filter_by(name="Weekly Verse").one()
        assert verse.pillar == "spiritual_education"

    def test_seed_is_idempotent(self, sync_session):
        seed_starter_templates(sync_session)
        seed_starter_templates(sync_session)
        templates = sync_session.query(Template).all()
        assert len(templates) == 4  # Not 8


class TestAsyncEngine:
    def test_get_async_engine_returns_engine(self):
        engine = get_async_engine("sqlite+aiosqlite:///:memory:")
        assert engine is not None

    def test_get_async_engine_caches(self):
        url = "sqlite+aiosqlite:///:memory:?cache_test=1"
        engine1 = get_async_engine(url)
        engine2 = get_async_engine(url)
        assert engine1 is engine2
