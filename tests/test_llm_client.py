import os
from unittest.mock import patch
from tools.llm_client import clean_json_response, get_llm_config


def test_clean_json_response_with_codeblock():
    raw = "```json\n{\"id\": \"q123\", \"answer\": \"A\"}\n```"
    parsed = clean_json_response(raw)
    assert parsed["id"] == "q123"
    assert parsed["answer"] == "A"


def test_clean_json_response_raw():
    raw = "{\"key\": \"value\"}"
    parsed = clean_json_response(raw)
    assert parsed["key"] == "value"


def test_get_llm_config_gemini():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key", "LLM_PROVIDER": "gemini"}, clear=True):
        provider, key, model, base_url = get_llm_config()
        assert provider == "gemini"
        assert key == "dummy_key"
        assert "gemini" in model


def test_get_llm_config_openai():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-dummy", "LLM_PROVIDER": "openai"}, clear=True):
        provider, key, model, base_url = get_llm_config()
        assert provider == "openai"
        assert key == "sk-dummy"


def test_get_llm_config_ollama():
    with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://localhost:11434/v1"}, clear=True):
        provider, key, model, base_url = get_llm_config()
        assert provider == "openai_compatible"
        assert base_url == "http://localhost:11434/v1/chat/completions"
