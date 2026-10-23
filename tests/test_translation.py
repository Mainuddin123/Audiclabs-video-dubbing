
import requests
import pytest

from src.translation import TranslationAdapter


def make_adapter(**kwargs):
    defaults = {
        "base_url": "https://mock-translation.example/v1",
        "api_key": "test-key",
        "model": "primary-model",
        "fallback_models": ["fallback-model"],
        "max_retries": 0,
    }
    defaults.update(kwargs)
    return TranslationAdapter(**defaults)


def test_empty_input_returns_empty_string():
    adapter = make_adapter()

    assert adapter.translate("", "English", "Hindi") == ""
    assert adapter.translate("   ", "English", "Hindi") == ""


def test_missing_configuration_raises_runtime_error(monkeypatch):
    # Prevent real .env settings from leaking into this test.
    monkeypatch.delenv("TRANSLATION_API_BASE_URL", raising=False)
    monkeypatch.delenv("TRANSLATION_API_KEY", raising=False)
    monkeypatch.delenv("TRANSLATION_MODEL", raising=False)
    monkeypatch.delenv("TRANSLATION_FALLBACK_MODEL_1", raising=False)
    monkeypatch.delenv("TRANSLATION_FALLBACK_MODEL_2", raising=False)

    adapter = TranslationAdapter(
        base_url="",
        api_key="",
        model="",
        fallback_models=[],
    )

    with pytest.raises(
        RuntimeError,
        match="TRANSLATION_API_BASE_URL",
    ):
        adapter.translate("Hello", "English", "Hindi")


def test_successful_translation_uses_primary_model(monkeypatch):
    adapter = make_adapter()
    calls = []

    def fake_translate(**kwargs):
        calls.append(kwargs)
        return "नमस्ते"

    monkeypatch.setattr(
        adapter,
        "_translate_with_model",
        fake_translate,
    )

    result = adapter.translate(
        "Hello",
        "English",
        "Hindi",
        max_chars=20,
    )

    assert result == "नमस्ते"
    assert len(calls) == 1
    assert calls[0]["model"] == "primary-model"
    assert calls[0]["max_chars"] == 20


def test_fallback_model_is_used_after_primary_fails(monkeypatch):
    adapter = make_adapter()
    calls = []

    def fake_translate_with_status(**kwargs):
        model = kwargs["model"]
        calls.append(model)

        if model == "primary-model":
            response = requests.Response()
            response.status_code = 503
            response.headers["Retry-After"] = "0"

            raise requests.HTTPError(
                "Service unavailable",
                response=response,
            )

        return "नमस्ते"

    monkeypatch.setattr(
        adapter,
        "_translate_with_model",
        fake_translate_with_status,
    )

    result = adapter.translate("Hello", "English", "Hindi")

    assert result == "नमस्ते"
    assert calls == ["primary-model", "fallback-model"]


def test_failed_models_return_empty_string(monkeypatch):
    adapter = make_adapter()

    def fake_translate(**kwargs):
        raise requests.ConnectionError("Mock connection failure")

    monkeypatch.setattr(
        adapter,
        "_translate_with_model",
        fake_translate,
    )

    assert adapter.translate("Hello", "English", "Hindi") == ""
