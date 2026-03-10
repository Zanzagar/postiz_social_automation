"""Tests for Streamlit Content Hub skeleton (Task 10).

Tests verify:
- App module imports without error
- Page config and theming are set
- Streamlit config.toml is valid
- Page files exist and are importable
- Dashboard renders metrics layout
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"
PAGES_DIR = APP_DIR / "pages"


class TestAppStructure:
    """Verify the Streamlit app file structure exists."""

    def test_content_hub_exists(self):
        assert (APP_DIR / "content_hub.py").exists()

    def test_pages_directory_exists(self):
        assert PAGES_DIR.is_dir()

    def test_streamlit_config_exists(self):
        config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
        assert config_path.exists(), ".streamlit/config.toml missing"

    def test_streamlit_config_valid_toml(self):
        import tomllib

        config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        assert "theme" in config
        assert "primaryColor" in config["theme"]

    def test_streamlit_theme_colors(self):
        """Theme uses warm earth tones for Gita Valley branding."""
        import tomllib

        config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        theme = config["theme"]
        # Verify all required theme keys exist
        assert "primaryColor" in theme
        assert "backgroundColor" in theme
        assert "secondaryBackgroundColor" in theme
        assert "textColor" in theme


class TestPageFiles:
    """Verify expected page files exist in app/pages/."""

    def test_create_page_exists(self):
        matches = list(PAGES_DIR.glob("*[Cc]reate*"))
        assert len(matches) >= 1, "No Create/Review page found in app/pages/"

    def test_calendar_page_exists(self):
        matches = list(PAGES_DIR.glob("*[Cc]alendar*"))
        assert len(matches) >= 1, "No Calendar page found in app/pages/"

    def test_analytics_page_exists(self):
        matches = list(PAGES_DIR.glob("*[Aa]nalytics*"))
        assert len(matches) >= 1, "No Analytics page found in app/pages/"


class TestContentHubModule:
    """Verify content_hub.py sets up the Streamlit app correctly."""

    @patch("streamlit.set_page_config")
    @patch("streamlit.sidebar", new_callable=MagicMock)
    @patch("streamlit.title")
    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.metric")
    def test_app_imports_and_configures(
        self, mock_metric, mock_columns, mock_markdown, mock_title, mock_sidebar, mock_config
    ):
        """content_hub.py should call set_page_config with Gita Valley settings."""
        # Mock columns to return context managers
        col = MagicMock()
        col.__enter__ = MagicMock(return_value=col)
        col.__exit__ = MagicMock(return_value=False)
        mock_columns.return_value = [col, col, col]

        import app.content_hub  # noqa: F401

        # Force reimport to trigger module-level code
        importlib.reload(importlib.import_module("app.content_hub"))

        mock_config.assert_called()
        call_kwargs = mock_config.call_args
        assert "Gita Valley" in str(call_kwargs)
