"""Tests validating content data repository JSON files."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "src" / "content_engine" / "data"


def _load_json(filename: str) -> dict | list:
    path = DATA_DIR / filename
    assert path.exists(), f"Data file missing: {filename}"
    return json.loads(path.read_text())


class TestFestivals:
    def test_file_parses(self) -> None:
        data = _load_json("festivals.json")
        assert "festivals" in data

    def test_festivals_have_required_fields(self) -> None:
        data = _load_json("festivals.json")
        for fest in data["festivals"]:
            assert "name" in fest
            assert "description" in fest

    def test_at_least_5_festivals(self) -> None:
        data = _load_json("festivals.json")
        assert len(data["festivals"]) >= 5


class TestCowProfiles:
    def test_file_parses(self) -> None:
        data = _load_json("cow-profiles.json")
        assert "cows" in data
        assert "oxen" in data

    def test_cows_have_names(self) -> None:
        data = _load_json("cow-profiles.json")
        for cow in data["cows"]:
            assert "name" in cow
            assert "personality" in cow

    def test_herd_stats(self) -> None:
        data = _load_json("cow-profiles.json")
        assert data["total_count"] > 0
        assert data["producing_milk"] > 0


class TestQuotes:
    def test_file_parses(self) -> None:
        data = _load_json("quotes.json")
        assert "quotes" in data

    def test_quotes_have_required_fields(self) -> None:
        data = _load_json("quotes.json")
        for quote in data["quotes"]:
            assert "text" in quote
            assert "source" in quote
            assert "theme" in quote


class TestFarmFacts:
    def test_file_parses(self) -> None:
        data = _load_json("farm-facts.json")
        assert data["name"] == "Gita Valley"

    def test_required_fields(self) -> None:
        data = _load_json("farm-facts.json")
        assert "location" in data
        assert "acreage" in data
        assert "website" in data
        assert "programs" in data


class TestBrandGuide:
    def test_file_parses(self) -> None:
        data = _load_json("brand-guide.json")
        assert data["name"] == "Gita Valley"

    def test_has_hashtag_strategy(self) -> None:
        data = _load_json("brand-guide.json")
        assert "hashtags" in data
        assert "instagram" in data["hashtags"]

    def test_voice_defined(self) -> None:
        data = _load_json("brand-guide.json")
        assert "voice" in data
        assert "style" in data["voice"]
