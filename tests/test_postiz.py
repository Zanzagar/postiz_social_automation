"""Tests for Postiz API client with mocked HTTP responses."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from content_engine.postiz import (
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_VIDEO_TYPES,
    MediaValidationError,
    PostizAPIError,
    PostizClient,
    parse_google_drive_url,
)


@pytest.fixture
def client():
    return PostizClient(api_key="test-api-key", base_url="https://postiz.example.com/api/public/v1")


class TestAuth:
    def test_auth_header_no_bearer_prefix(self, client) -> None:
        """Postiz uses 'Authorization: <key>' without Bearer prefix."""
        assert client.session.headers["Authorization"] == "test-api-key"

    def test_custom_base_url(self, client) -> None:
        assert client.base_url == "https://postiz.example.com/api/public/v1"


class TestListIntegrations:
    @patch("content_engine.postiz.requests.Session.request")
    def test_returns_integrations(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "int_1", "providerIdentifier": "instagram", "name": "GV Instagram"},
            {"id": "int_2", "providerIdentifier": "facebook", "name": "GV Facebook"},
        ]
        mock_request.return_value = mock_resp

        integrations = client.list_integrations()

        assert len(integrations) == 2
        assert integrations[0]["id"] == "int_1"
        mock_request.assert_called_once_with(
            "GET",
            "https://postiz.example.com/api/public/v1/integrations",
        )


class TestCreateDraftPost:
    @patch("content_engine.postiz.requests.Session.request")
    def test_creates_post_with_correct_payload(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "post_123", "status": "draft"}
        mock_request.return_value = mock_resp

        result = client.create_draft_post(
            content="Baby calf born this morning! #farmlife",
            platform_ids=["int_1", "int_2"],
            scheduled_at="2026-03-01T10:00:00Z",
        )

        assert result["id"] == "post_123"
        call_kwargs = mock_request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["content"] == "Baby calf born this morning! #farmlife"
        assert payload["integrations"] == ["int_1", "int_2"]
        assert payload["scheduledAt"] == "2026-03-01T10:00:00Z"

    @patch("content_engine.postiz.requests.Session.request")
    def test_creates_post_without_optional_fields(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "post_456"}
        mock_request.return_value = mock_resp

        result = client.create_draft_post(
            content="Simple post",
            platform_ids=["int_1"],
        )

        assert result["id"] == "post_456"


class TestRateLimitRetry:
    @patch("content_engine.postiz.time.sleep")
    @patch("content_engine.postiz.requests.Session.request")
    def test_retries_on_429(self, mock_request, mock_sleep, client) -> None:
        """Rate limit (429) triggers retry with backoff."""
        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.raise_for_status.side_effect = requests.HTTPError(response=rate_resp)

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = []

        mock_request.side_effect = [rate_resp, ok_resp]

        result = client.list_integrations()

        assert result == []
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once()

    @patch("content_engine.postiz.time.sleep")
    @patch("content_engine.postiz.requests.Session.request")
    def test_raises_after_max_retries(self, mock_request, mock_sleep, client) -> None:
        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.raise_for_status.side_effect = requests.HTTPError(response=rate_resp)

        mock_request.return_value = rate_resp

        with pytest.raises(PostizAPIError, match="Rate limit"):
            client.list_integrations()

        assert mock_request.call_count == 3


class TestGetPostAnalytics:
    """Converged on canonical GET /analytics/post/{postId} (I2 resolved)."""

    @patch("content_engine.postiz.requests.Session.request")
    def test_calls_canonical_analytics_endpoint(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "likes": 150,
            "comments": 23,
            "shares": 8,
            "reach": 900,
            "impressions": 2000,
        }
        mock_request.return_value = mock_resp

        client.get_post_analytics(post_id="post_123", pillar="Cow Life")

        mock_request.assert_called_once_with(
            "GET",
            "https://postiz.example.com/api/public/v1/analytics/post/post_123",
        )

    @patch("content_engine.postiz.requests.Session.request")
    def test_returns_post_performance_with_unified_fields(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "likes": 150,
            "comments": 23,
            "shares": 8,
            "reach": 900,
            "impressions": 2000,
            "integration": {"providerIdentifier": "instagram"},
            "publishedAt": "2026-02-20T14:00:00Z",
        }
        mock_request.return_value = mock_resp

        perf = client.get_post_analytics(post_id="post_123", pillar="Cow Life")

        assert perf.post_id == "post_123"
        assert perf.likes == 150
        assert perf.comments == 23
        assert perf.shares == 8
        assert perf.reach == 900
        assert perf.impressions == 2000

    @patch("content_engine.postiz.requests.Session.request")
    def test_engagement_rate_computed_our_side(self, mock_request, client) -> None:
        """engagement_rate = (likes+comments+shares)/reach, never read from Postiz."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "likes": 60,
            "comments": 30,
            "shares": 10,
            "reach": 1000,
            "impressions": 1500,
            "engagement_rate": 99.9,  # must be ignored — computed our side
        }
        mock_request.return_value = mock_resp

        perf = client.get_post_analytics(post_id="p1", pillar="Cow Life")

        assert perf.engagement_rate == pytest.approx(0.1)  # (60+30+10)/1000

    @patch("content_engine.postiz.requests.Session.request")
    def test_engagement_rate_zero_when_no_reach(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"likes": 5, "comments": 1, "shares": 0, "reach": 0}
        mock_request.return_value = mock_resp

        perf = client.get_post_analytics(post_id="p1", pillar="Cow Life")

        assert perf.engagement_rate == 0.0

    @patch("content_engine.postiz.requests.Session.request")
    def test_missing_metrics_default_to_zero(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_request.return_value = mock_resp

        perf = client.get_post_analytics(post_id="p1", pillar="Cow Life")

        assert perf.likes == 0
        assert perf.reach == 0
        assert perf.impressions == 0
        assert perf.engagement_rate == 0.0


class TestFetchPostAnalytics:
    """Raw canonical fetch shared by PostizAnalyticsSync."""

    @patch("content_engine.postiz.requests.Session.request")
    def test_returns_normalized_field_set(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "likes": 45,
            "comments": 8,
            "shares": 12,
            "reach": 500,
            "impressions": 1200,
        }
        mock_request.return_value = mock_resp

        metrics = client.fetch_post_analytics("post_9")

        assert metrics["likes"] == 45
        assert metrics["comments"] == 8
        assert metrics["shares"] == 12
        assert metrics["reach"] == 500
        assert metrics["impressions"] == 1200

    @patch("content_engine.postiz.requests.Session.request")
    def test_tolerates_nested_statistics_payload(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"statistics": {"likes": 7, "reach": 100}}
        mock_request.return_value = mock_resp

        metrics = client.fetch_post_analytics("post_9")

        assert metrics["likes"] == 7
        assert metrics["reach"] == 100
        assert metrics["shares"] == 0


class TestGetIntegrationAnalytics:
    @patch("content_engine.postiz.requests.Session.request")
    def test_calls_platform_level_endpoint(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "likes": 500,
            "comments": 80,
            "shares": 40,
            "reach": 9000,
            "impressions": 15000,
        }
        mock_request.return_value = mock_resp

        metrics = client.get_integration_analytics("int_42")

        mock_request.assert_called_once_with(
            "GET",
            "https://postiz.example.com/api/public/v1/analytics/int_42",
        )
        assert metrics["likes"] == 500
        assert metrics["impressions"] == 15000


class TestErrorHandling:
    @patch("content_engine.postiz.time.sleep")
    @patch("content_engine.postiz.requests.Session.request")
    def test_retries_and_raises_on_server_error(self, mock_request, mock_sleep, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        mock_request.return_value = mock_resp

        with pytest.raises(PostizAPIError, match="Server error 500"):
            client.list_integrations()

        # Verify it retried 3 times before giving up
        assert mock_request.call_count == 3


class TestParseGoogleDriveUrl:
    """Subtask 18.1: Google Drive URL parsing."""

    def test_converts_file_view_url(self) -> None:
        url = "https://drive.google.com/file/d/abc123xyz/view?usp=sharing"
        assert (
            parse_google_drive_url(url)
            == "https://drive.google.com/uc?export=download&id=abc123xyz"
        )

    def test_converts_open_url(self) -> None:
        url = "https://drive.google.com/open?id=abc123xyz"
        assert (
            parse_google_drive_url(url)
            == "https://drive.google.com/uc?export=download&id=abc123xyz"
        )

    def test_passes_through_direct_url(self) -> None:
        """Non-Google-Drive URLs are returned as-is."""
        url = "https://example.com/image.jpg"
        assert parse_google_drive_url(url) == url

    def test_converts_uc_export_url(self) -> None:
        """Already-direct Google Drive URLs are returned as-is."""
        url = "https://drive.google.com/uc?export=download&id=abc123xyz"
        assert parse_google_drive_url(url) == url

    def test_raises_on_unrecognized_drive_url(self) -> None:
        """Google Drive URL that can't be parsed raises ValueError."""
        url = "https://drive.google.com/some/unknown/path"
        with pytest.raises(ValueError, match="Cannot extract file ID"):
            parse_google_drive_url(url)


class TestMediaValidation:
    """Subtask 18.2: Format, size, and type validation."""

    def test_supported_image_types_defined(self) -> None:
        assert "image/jpeg" in SUPPORTED_IMAGE_TYPES
        assert "image/png" in SUPPORTED_IMAGE_TYPES
        assert "image/webp" in SUPPORTED_IMAGE_TYPES

    def test_supported_video_types_defined(self) -> None:
        assert "video/mp4" in SUPPORTED_VIDEO_TYPES

    def test_size_limits_defined(self) -> None:
        assert MAX_IMAGE_SIZE == 10 * 1024 * 1024  # 10 MB
        assert MAX_VIDEO_SIZE == 100 * 1024 * 1024  # 100 MB

    def test_validate_media_rejects_unsupported_type(self, client) -> None:
        with pytest.raises(MediaValidationError, match="Unsupported media type"):
            client.validate_media(content_type="application/pdf", file_size=1000)

    def test_validate_media_rejects_oversized_image(self, client) -> None:
        with pytest.raises(MediaValidationError, match="exceeds .* limit"):
            client.validate_media(
                content_type="image/jpeg",
                file_size=MAX_IMAGE_SIZE + 1,
            )

    def test_validate_media_rejects_oversized_video(self, client) -> None:
        with pytest.raises(MediaValidationError, match="exceeds .* limit"):
            client.validate_media(
                content_type="video/mp4",
                file_size=MAX_VIDEO_SIZE + 1,
            )

    def test_validate_media_accepts_valid_image(self, client) -> None:
        # Should not raise
        client.validate_media(content_type="image/jpeg", file_size=5000)

    def test_validate_media_accepts_valid_video(self, client) -> None:
        client.validate_media(content_type="video/mp4", file_size=50_000_000)


class TestUploadMedia:
    """Subtask 18.3: Full download-validate-upload pipeline."""

    @patch("content_engine.postiz.requests.get")
    @patch("content_engine.postiz.requests.Session.request")
    def test_downloads_and_uploads_image(self, mock_session_req, mock_get, client) -> None:
        # Mock download
        download_resp = MagicMock()
        download_resp.headers = {"Content-Type": "image/jpeg", "Content-Length": "5000"}
        download_resp.iter_content.return_value = [b"fake-image-data"]
        download_resp.raise_for_status = MagicMock()
        mock_get.return_value = download_resp

        # Mock upload
        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.json.return_value = {"id": "media_abc123"}
        mock_session_req.return_value = upload_resp

        media_id = client.upload_media("https://example.com/photo.jpg")

        assert media_id == "media_abc123"
        mock_get.assert_called_once()

    @patch("content_engine.postiz.requests.get")
    def test_rejects_unsupported_format(self, mock_get, client) -> None:
        download_resp = MagicMock()
        download_resp.headers = {"Content-Type": "application/pdf", "Content-Length": "5000"}
        download_resp.iter_content.return_value = [b"fake-pdf-data"]
        download_resp.raise_for_status = MagicMock()
        mock_get.return_value = download_resp

        with pytest.raises(MediaValidationError, match="Unsupported media type"):
            client.upload_media("https://example.com/doc.pdf")

    @patch("content_engine.postiz.requests.get")
    def test_parses_google_drive_url_before_download(self, mock_get, client) -> None:
        download_resp = MagicMock()
        download_resp.headers = {"Content-Type": "image/png", "Content-Length": "3000"}
        download_resp.iter_content.return_value = [b"fake-png"]
        download_resp.raise_for_status = MagicMock()
        mock_get.return_value = download_resp

        # Also mock the upload
        with patch("content_engine.postiz.requests.Session.request") as mock_session_req:
            upload_resp = MagicMock()
            upload_resp.status_code = 200
            upload_resp.json.return_value = {"id": "media_xyz"}
            mock_session_req.return_value = upload_resp

            client.upload_media("https://drive.google.com/file/d/abc123/view?usp=sharing")

        # Should have converted the URL before downloading
        actual_url = mock_get.call_args[0][0]
        assert "uc?export=download" in actual_url

    @patch("content_engine.postiz.requests.get")
    @patch("content_engine.postiz.requests.Session.request")
    def test_cleans_up_temp_file(self, mock_session_req, mock_get, client) -> None:
        download_resp = MagicMock()
        download_resp.headers = {"Content-Type": "image/jpeg", "Content-Length": "5000"}
        download_resp.iter_content.return_value = [b"fake-image"]
        download_resp.raise_for_status = MagicMock()
        mock_get.return_value = download_resp

        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.json.return_value = {"id": "media_tmp"}
        mock_session_req.return_value = upload_resp

        client.upload_media("https://example.com/photo.jpg")

        # Temp files should be cleaned up (no lingering files)
        import tempfile

        temp_dir = Path(tempfile.gettempdir())
        leftover = list(temp_dir.glob("postiz_media_*"))
        assert len(leftover) == 0
