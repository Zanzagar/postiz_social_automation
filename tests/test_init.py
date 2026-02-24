"""Smoke tests for project initialization."""

from content_engine import __version__


def test_version_is_set() -> None:
    assert __version__ == "0.1.0"


def test_package_imports() -> None:
    """Verify all content engine modules are importable."""
    import content_engine.sheets
    import content_engine.postiz
    import content_engine.generator
    import content_engine.intelligence
    import content_engine.scheduler
    import content_engine.models
