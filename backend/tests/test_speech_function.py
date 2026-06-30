import json
import importlib
import importlib.util
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def speech_module(monkeypatch):
    mock_ff = MagicMock()
    mock_ff.http = lambda func: func
    monkeypatch.setitem(sys.modules, "functions_framework", mock_ff)

    mock_google = types.ModuleType("google")
    mock_google.__path__ = []
    cloud_mod = types.ModuleType("google.cloud")
    cloud_mod.__path__ = []
    firestore_mod = MagicMock()
    texttospeech_mod = types.ModuleType("google.cloud.texttospeech")
    texttospeech_mod.AudioEncoding = SimpleNamespace(MP3="MP3")
    texttospeech_mod.AudioConfig = lambda **kwargs: SimpleNamespace(**kwargs)
    texttospeech_mod.SsmlVoiceGender = SimpleNamespace(FEMALE="FEMALE")
    texttospeech_mod.VoiceSelectionParams = lambda **kwargs: SimpleNamespace(**kwargs)
    texttospeech_mod.SynthesisInput = lambda text: SimpleNamespace(text=text)
    texttospeech_mod.TextToSpeechClient = MagicMock()
    storage_mod = types.ModuleType("google.cloud.storage")
    storage_mod.Client = MagicMock()
    cloud_mod.texttospeech = texttospeech_mod
    cloud_mod.storage = storage_mod
    mock_google.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", mock_google)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.texttospeech", texttospeech_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_mod)

    for name in ("main", "auth_utils", "firestore_utils", "course_utils", "utils"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    func_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/speech")
    )
    if func_path not in sys.path:
        sys.path.insert(0, func_path)

    module_name = "speech_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/speech/main.py")
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def speech_request():
    request = MagicMock()
    request.headers = {"X-Timestamp": "1", "X-Sign": "sig", "X-Key": "key"}
    request.data = b'{"languageCode":"en","text":"Hello"}'
    request.get_json.return_value = {
        "traceId": "trace",
        "sessionId": "session",
        "languageCode": "en",
    }
    return request


def _configure_speech_happy_path(module, monkeypatch, blob_exists: bool):
    monkeypatch.setenv("SPEECH_FILE_BUCKET", "speech-bucket")
    monkeypatch.setenv("XIAOICE_CHAT_SECRET_KEY", "secret")
    monkeypatch.setenv("XIAOICE_CHAT_ACCESS_KEY", "key")
    monkeypatch.setattr(module, "validate_authentication", lambda _request: None)
    monkeypatch.setattr(module, "get_config", lambda: {"welcome_messages": {"en": "Hello"}})
    monkeypatch.setattr(module.course_utils, "get_voice_params", lambda *_args: SimpleNamespace(name="voice"))
    monkeypatch.setattr(
        module.utils,
        "synthesize_speech_with_retry",
        lambda *_args, **_kwargs: SimpleNamespace(audio_content=b"mp3"),
    )

    storage_client = module.storage.Client.return_value
    bucket = storage_client.bucket.return_value
    blob = bucket.blob.return_value
    blob.exists.return_value = blob_exists
    blob.upload_from_string = MagicMock()
    module.texttospeech.TextToSpeechClient.return_value = MagicMock()
    return blob


def test_speech_generates_and_caches_when_blob_missing(speech_module, speech_request, monkeypatch):
    blob = _configure_speech_happy_path(speech_module, monkeypatch, blob_exists=False)

    response = speech_module.speech(speech_request)

    assert response[1] == 200
    payload = json.loads(response[0])
    assert payload["voiceUrl"].startswith("https://storage.googleapis.com/speech-bucket/")
    assert blob.upload_from_string.called
    speech_module.texttospeech.TextToSpeechClient.assert_called_once()


def test_speech_reuses_cached_blob_when_present(speech_module, speech_request, monkeypatch):
    blob = _configure_speech_happy_path(speech_module, monkeypatch, blob_exists=True)

    response = speech_module.speech(speech_request)

    assert response[1] == 200
    assert not blob.upload_from_string.called
    speech_module.texttospeech.TextToSpeechClient.assert_not_called()
