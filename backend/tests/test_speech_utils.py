import importlib.util
import os
import sys
import types

import pytest

pytestmark = pytest.mark.unit


def _load_speech_utils(monkeypatch):
    module_name = "speech_utils_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/speech/utils.py")
    )
    fake_tts = types.SimpleNamespace(
        SynthesisInput=lambda text: types.SimpleNamespace(text=text)
    )
    google_module = types.ModuleType("google")
    google_module.__path__ = []
    cloud_module = types.ModuleType("google.cloud")
    cloud_module.texttospeech = fake_tts
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.texttospeech", fake_tts)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_sanitize_text_for_tts_supports_normal_and_aggressive_modes(monkeypatch):
    module = _load_speech_utils(monkeypatch)

    assert module.sanitize_text_for_tts("Hello ⟪world⟫  ") == "Hello world"
    assert module.sanitize_text_for_tts("A&B <tag>", aggressive=True) == "AandB tag"


def test_synthesize_speech_with_retry_uses_clean_text_first_then_aggressive_retry(
    monkeypatch,
):
    module = _load_speech_utils(monkeypatch)

    calls = []

    class Client:
        def synthesize_speech(self, request):
            calls.append(request["input"].text)
            if len(calls) == 1:
                raise RuntimeError("transient failure")
            return types.SimpleNamespace(audio_content=b"ok")

    response = module.synthesize_speech_with_retry(
        Client(),
        "Hello ⟪world⟫ & <tag>",
        voice="voice",
        audio_config="audio-config",
        max_retries=1,
    )

    assert response.audio_content == b"ok"
    assert calls == ["Hello world & <tag>", "Hello world and tag"]


def test_synthesize_speech_with_retry_rejects_empty_retry_text(monkeypatch):
    module = _load_speech_utils(monkeypatch)

    class Client:
        def synthesize_speech(self, request):
            raise RuntimeError("always fails")

    with pytest.raises(ValueError, match="became empty"):
        module.synthesize_speech_with_retry(
            Client(),
            "\x01\x02\x03",
            voice="voice",
            audio_config="audio-config",
            max_retries=1,
        )
