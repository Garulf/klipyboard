from __future__ import annotations

from klipyboard.settings import Settings


def test_from_raw_reads_api_key():
    settings = Settings.from_raw({"api_key": "  secret123  "})
    assert settings.api_key == "secret123"
    assert settings.has_api_key is True


def test_from_raw_missing_key_defaults_empty():
    settings = Settings.from_raw({})
    assert settings.api_key == ""
    assert settings.has_api_key is False


def test_from_raw_non_string_value_defaults_empty():
    settings = Settings.from_raw({"api_key": 12345})
    assert settings.api_key == ""
    assert settings.has_api_key is False
