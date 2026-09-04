import os
from unittest.mock import MagicMock, patch

import pytest

from pdf_school.core.llm_client import (
    call_llm,
    clean_json_response,
    generate_structured_json,
    get_llm_config,
)


def test_clean_json_response_with_codeblock():
    raw = '```json\n{"id": "q123", "answer": "A"}\n```'
    parsed = clean_json_response(raw)
    assert parsed["id"] == "q123"
    assert parsed["answer"] == "A"


def test_clean_json_response_raw():
    raw = '{"key": "value"}'
    parsed = clean_json_response(raw)
    assert parsed["key"] == "value"


def test_get_llm_config_gemini():
    with patch.dict(
        os.environ, {"GEMINI_API_KEY": "dummy_key", "LLM_PROVIDER": "gemini"}, clear=True
    ):
        provider, key, model, base_url = get_llm_config()
        assert provider == "gemini"
        assert key == "dummy_key"
        assert "gemini" in model


def test_get_llm_config_openai():
    with patch.dict(
        os.environ, {"OPENAI_API_KEY": "sk-dummy", "LLM_PROVIDER": "openai"}, clear=True
    ):
        provider, key, model, base_url = get_llm_config()
        assert provider == "openai"
        assert key == "sk-dummy"


def test_get_llm_config_anthropic():
    with patch.dict(
        os.environ, {"ANTHROPIC_API_KEY": "sk-ant-dummy", "LLM_PROVIDER": "anthropic"}, clear=True
    ):
        provider, key, model, base_url = get_llm_config()
        assert provider == "anthropic"
        assert key == "sk-ant-dummy"


def test_get_llm_config_ollama():
    with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://localhost:11434/v1"}, clear=True):
        provider, key, model, base_url = get_llm_config()
        assert provider == "openai_compatible"
        assert base_url == "http://localhost:11434/v1/chat/completions"


def test_call_llm_missing_provider():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="No LLM provider configured"):
            call_llm("sys", "user")


def test_call_llm_gemini():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"result": "success"}'}]}}]
    }
    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}, clear=True):
        with patch("requests.post", return_value=mock_resp):
            out = call_llm("sys", "user")
            assert '{"result": "success"}' in out


def test_call_llm_anthropic():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"content": [{"text": '{"result": "anthropic_success"}'}]}
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy_key"}, clear=True):
        with patch("requests.post", return_value=mock_resp):
            out = call_llm("sys", "user")
            assert "anthropic_success" in out


def test_call_llm_openai():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"result": "openai_success"}'}}]
    }
    with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy_key"}, clear=True):
        with patch("requests.post", return_value=mock_resp):
            out = call_llm("sys", "user")
            assert "openai_success" in out


def test_generate_structured_json():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '```json\n{"status": "ok"}\n```'}}]
    }
    with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy_key"}, clear=True):
        with patch("requests.post", return_value=mock_resp):
            data = generate_structured_json("sys", "user")
            assert data["status"] == "ok"
