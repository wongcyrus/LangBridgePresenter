import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def voice_chat_module(monkeypatch):
    mock_ff = MagicMock()
    mock_ff.http = lambda func: func
    monkeypatch.setitem(sys.modules, "functions_framework", mock_ff)

    flask_mod = types.ModuleType("flask")
    flask_mod.Request = object
    flask_mod.Response = object
    flask_mod.stream_with_context = lambda fn: fn
    monkeypatch.setitem(sys.modules, "flask", flask_mod)

    mock_firebase_admin = types.ModuleType("firebase_admin")
    mock_firebase_admin._apps = []
    mock_firebase_admin.initialize_app = MagicMock()
    auth_mod = types.ModuleType("firebase_admin.auth")
    auth_mod.verify_id_token = MagicMock()
    mock_firebase_admin.auth = auth_mod
    monkeypatch.setitem(sys.modules, "firebase_admin", mock_firebase_admin)
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", auth_mod)

    google_mod = types.ModuleType("google")
    google_mod.__path__ = []
    cloud_mod = types.ModuleType("google.cloud")
    cloud_mod.__path__ = []
    firestore_mod = types.ModuleType("google.cloud.firestore")
    firestore_mod.Client = MagicMock()
    storage_mod = types.ModuleType("google.cloud.storage")
    storage_mod.Client = MagicMock()
    tts_mod = types.ModuleType("google.cloud.texttospeech")
    tts_mod.TextToSpeechClient = MagicMock()
    cloud_mod.firestore = firestore_mod
    cloud_mod.storage = storage_mod
    cloud_mod.texttospeech = tts_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.texttospeech", tts_mod)

    genai_pkg = types.ModuleType("google.genai")
    genai_pkg.Client = MagicMock()
    monkeypatch.setitem(sys.modules, "google.genai", genai_pkg)
    google_mod.genai = genai_pkg

    module_name = "voice_chat_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/voice-chat/main.py")
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mock_request():
    req = MagicMock()
    req.headers = {}
    req.method = "POST"
    req.get_json.return_value = {"question": "hello"}
    return req


def test_voice_chat_rejects_unauthenticated(voice_chat_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_module,
        "_verify_firebase_user",
        lambda _request: (_ for _ in ()).throw(PermissionError("bad")),
    )
    body, status, _headers = voice_chat_module.voice_chat(mock_request)
    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_voice_chat_requires_lease_session_id(voice_chat_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_module,
        "_verify_firebase_user",
        lambda _request: {"uid": "u-1", "email": "u1@example.com"},
    )
    body, status, _headers = voice_chat_module.voice_chat(mock_request)
    assert status == 400
    assert json.loads(body)["error"] == "lease_session_id is required"


def test_voice_chat_rejects_invalid_lease(voice_chat_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {"question": "next slide", "lease_session_id": "bad-lease"}
    monkeypatch.setattr(
        voice_chat_module,
        "_verify_firebase_user",
        lambda _request: {"uid": "u-2", "email": "u2@example.com"},
    )
    monkeypatch.setattr(voice_chat_module, "_has_voice_access", lambda _decoded, _db: True)
    monkeypatch.setattr(
        voice_chat_module,
        "_validate_live_lease",
        lambda _db, _uid, _lease: (_ for _ in ()).throw(PermissionError("Invalid voice live lease")),
    )
    voice_chat_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = voice_chat_module.voice_chat(mock_request)
    assert status == 403
    assert json.loads(body)["error"] == "Invalid voice live lease"


def test_voice_chat_returns_commands_for_command_prompt(voice_chat_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {
        "question": "next slide please",
        "lease_session_id": "lease-1",
        "courseId": "course-a",
        "presentationId": "ppt-1",
        "slideId": "3",
        "languageCode": "en-US",
    }
    monkeypatch.setattr(
        voice_chat_module,
        "_verify_firebase_user",
        lambda _request: {"uid": "u-3", "email": "u3@example.com"},
    )
    monkeypatch.setattr(voice_chat_module, "_has_voice_access", lambda _decoded, _db: True)
    monkeypatch.setattr(
        voice_chat_module,
        "_validate_live_lease",
        lambda _db, _uid, _lease: {"course_id": "course-a", "presentation_id": "ppt-1", "slide_id": "3"},
    )
    monkeypatch.setattr(voice_chat_module, "_enforce_usage_limit", lambda _db, _uid: {"minute_used": 1})
    monkeypatch.setattr(voice_chat_module, "_synthesize_answer_audio", lambda *_args, **_kwargs: "https://audio.local/a.mp3")
    voice_chat_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = voice_chat_module.voice_chat(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["commands"] == [{"name": "navigate_slide", "args": {"direction": "next"}}]
    assert payload["audioUrl"] == "https://audio.local/a.mp3"
