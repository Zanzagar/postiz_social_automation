"""Tests for Postiz API client with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from content_engine.models import ContentPillar
from content_engine.postiz import PostizAPIError, PostizClient


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
    @patch("content_engine.postiz.requests.Session.request")
    def test_returns_post_performance(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "post_123",
            "integration": {"providerIdentifier": "instagram"},
            "statistics": {
                "likes": 150,
                "comments": 23,
                "shares": 8,
            },
            "publishedAt": "2026-02-20T14:00:00Z",
        }
        mock_request.return_value = mock_resp

        perf = client.get_post_analytics(
            post_id="post_123",
            pillar=ContentPillar.COW_LIFE,
        )

        assert perf.post_id == "post_123"
        assert perf.likes == 150
        assert perf.comments == 23


class TestErrorHandling:
    @patch("content_engine.postiz.requests.Session.request")
    def test_raises_on_server_error(self, mock_request, client) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)

        mock_request.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            client.list_integrations()
