"""Tests for src/config.py — verifies env var fallback works without Streamlit."""

import sys
import unittest.mock as mock

import pytest


def _get_config_with_failing_secrets():
    """Return get_config() with st.secrets.get patched to always raise."""
    if "src.config" in sys.modules:
        del sys.modules["src.config"]
    import src.config as cfg_module

    # Patch the st object inside the config module so secrets.get raises
    mock_st = mock.MagicMock()
    mock_st.secrets.get.side_effect = Exception("no secrets")
    cfg_module.st = mock_st
    return cfg_module.get_config


class TestGetConfigEnvFallback:
    def test_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("BASE_URL", "https://env.example.com")
        result = _get_config_with_failing_secrets()()
        assert result["base_url"] == "https://env.example.com"

    def test_mineru_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("MINERU_API_KEY", "test-key-123")
        result = _get_config_with_failing_secrets()()
        assert result["mineru_api_key"] == "test-key-123"

    def test_default_base_url_when_no_env_or_secrets(self, monkeypatch):
        monkeypatch.delenv("BASE_URL", raising=False)
        result = _get_config_with_failing_secrets()()
        assert result["base_url"] == "https://www.parliament.go.ke"

    def test_mineru_api_key_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("MINERU_API_KEY", raising=False)
        result = _get_config_with_failing_secrets()()
        assert result["mineru_api_key"] is None

    def test_scrape_headers_parsed_from_env(self, monkeypatch):
        monkeypatch.setenv("SCRAPE_HEADERS", '{"User-Agent": "test-agent"}')
        result = _get_config_with_failing_secrets()()
        assert result["scrape_headers"] == {"User-Agent": "test-agent"}
