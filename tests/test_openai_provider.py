"""Tests for opt-in OpenAI-compatible cloud provider."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from arbora.cli.session import list_provider_choices, provider_privacy_notice, select_provider
from arbora.providers.openai_compatible import OpenAICompatibleProvider, cloud_provider_configured


def test_cloud_provider_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        provider = OpenAICompatibleProvider()
        assert provider.available() is False
        with pytest.raises(RuntimeError, match="ARBORA_OPENAI_API_KEY"):
            provider.complete("hello")


def test_cloud_provider_complete_mocked():
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://example.test/v1")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": '{"rationale":"ok","steps":[]}'}}]}
            ).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        text = provider.complete("plan this")
    assert "rationale" in text


def test_select_provider_openai_when_configured():
    with patch.dict("os.environ", {"ARBORA_OPENAI_API_KEY": "secret"}):
        provider = select_provider("openai")
        assert provider.name == "openai"
        assert cloud_provider_configured() is True
        assert "openai" in list_provider_choices()


def test_provider_privacy_notice_for_cloud():
    provider = OpenAICompatibleProvider(api_key="secret")
    notice = provider_privacy_notice(provider)
    assert notice is not None
    assert "leaves" in notice.lower() or "sent" in notice.lower()
