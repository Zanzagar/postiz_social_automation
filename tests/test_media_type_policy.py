"""Regression tests for media-type policy consistency (POSTIZ_CONTRACT §2, I1).

Postiz upload is the hard gate and it rejects GIF. Every earlier layer
(pre-generation validator, media catalog upload API, simple upload API)
must therefore reject GIF up front so users get warned early instead of
failing late at publish time.

These tests import the allowlists read-only from all layers and pin the
policy so a future edit to any single layer cannot silently reintroduce
the inconsistency.
"""

from api.routes.media import ALLOWED_TYPES as MEDIA_CATALOG_ALLOWED_TYPES
from api.routes.upload import ALLOWED_TYPES as SIMPLE_UPLOAD_ALLOWED_TYPES
from content_engine.postiz import SUPPORTED_IMAGE_TYPES, SUPPORTED_VIDEO_TYPES
from content_engine.validator import SUPPORTED_MEDIA_TYPES

POSTIZ_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_VIDEO_TYPES


class TestGifRejectedAtEveryLayer:
    """POSTIZ_CONTRACT I1: GIF must be in NO allowlist."""

    def test_gif_not_in_pre_generation_validator(self) -> None:
        assert "image/gif" not in SUPPORTED_MEDIA_TYPES

    def test_gif_not_in_media_catalog_upload_api(self) -> None:
        assert "image/gif" not in MEDIA_CATALOG_ALLOWED_TYPES

    def test_gif_not_in_simple_upload_api(self) -> None:
        assert "image/gif" not in SIMPLE_UPLOAD_ALLOWED_TYPES

    def test_gif_not_in_postiz_client(self) -> None:
        assert "image/gif" not in POSTIZ_TYPES


class TestLayersAgreeWithPostizGate:
    """The layers must agree: nothing the early layers admit for publishing
    should die at the Postiz gate, and nothing Postiz accepts should be
    blocked earlier."""

    def test_validator_matches_postiz_gate_exactly(self) -> None:
        # The pre-generation validator gates publish-bound media, so its
        # allowlist must equal what the Postiz client will actually accept.
        assert SUPPORTED_MEDIA_TYPES == POSTIZ_TYPES

    def test_postiz_types_all_accepted_by_media_catalog_api(self) -> None:
        # The media catalog may accept extra formats for non-publish uses
        # (e.g. video/quicktime, video/webm), but must never reject a type
        # the Postiz gate supports.
        assert POSTIZ_TYPES <= MEDIA_CATALOG_ALLOWED_TYPES

    def test_simple_upload_matches_postiz_gate_exactly(self) -> None:
        assert SIMPLE_UPLOAD_ALLOWED_TYPES == POSTIZ_TYPES
