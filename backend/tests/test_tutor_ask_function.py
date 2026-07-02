import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def tutor_ask_module(monkeypatch):
    mock_ff = MagicMock()
    mock_ff.http = lambda func: func
    monkeypatch.setitem(sys.modules, "functions_framework", mock_ff)

    flask_mod = types.ModuleType("flask")
    flask_mod.Request = object
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
    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = MagicMock()
    google_mod.genai = genai_mod
    cloud_mod = types.ModuleType("google.cloud")
    cloud_mod.__path__ = []
    firestore_mod = types.ModuleType("google.cloud.firestore")
    firestore_mod.Client = MagicMock()
    firestore_mod.SERVER_TIMESTAMP = object()
    firestore_mod.transactional = lambda fn: fn
    storage_mod = types.ModuleType("google.cloud.storage")
    storage_mod.Client = MagicMock()
    tts_mod = types.ModuleType("google.cloud.texttospeech")
    tts_mod.TextToSpeechClient = MagicMock()
    tts_mod.SsmlVoiceGender = types.SimpleNamespace(FEMALE="FEMALE")
    tts_mod.AudioEncoding = types.SimpleNamespace(MP3="MP3")
    tts_mod.VoiceSelectionParams = MagicMock()
    tts_mod.AudioConfig = MagicMock()
    tts_mod.SynthesisInput = MagicMock()
    cloud_mod.firestore = firestore_mod
    cloud_mod.storage = storage_mod
    cloud_mod.texttospeech = tts_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.texttospeech", tts_mod)

    module_name = "tutor_ask_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/tutor-ask/main.py")
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
    req.get_json.return_value = {}
    return req


def test_tutor_ask_rejects_unauthenticated(tutor_ask_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        tutor_ask_module,
        "_verify_firebase_user",
        lambda _request: (_ for _ in ()).throw(PermissionError("bad")),
    )

    body, status, _headers = tutor_ask_module.tutor_ask(mock_request)
    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_tutor_ask_requires_question(tutor_ask_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {"courseId": "showcase", "presentationId": "cloudtech_pptx", "slideId": "1"}
    monkeypatch.setattr(tutor_ask_module, "_verify_firebase_user", lambda _request: {"uid": "u-1"})

    body, status, _headers = tutor_ask_module.tutor_ask(mock_request)
    assert status == 400
    assert json.loads(body)["error"] == "question is required"


def test_tutor_ask_rejects_long_question(tutor_ask_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {
        "question": "a" * 501,
        "courseId": "showcase",
        "presentationId": "cloudtech_pptx",
        "slideId": "1",
    }
    monkeypatch.setattr(tutor_ask_module, "_verify_firebase_user", lambda _request: {"uid": "u-1"})

    body, status, _headers = tutor_ask_module.tutor_ask(mock_request)
    assert status == 400
    assert json.loads(body)["error"] == "question is too long (max 500 chars)"


def test_build_prompt_enforces_slide_scope(tutor_ask_module):
    prompt = tutor_ask_module._build_prompt(
        "Tell me about football news",
        "en-US",
        {
            "languages": {"en": {"text": "Cloud computing has IaaS, PaaS, SaaS."}},
            "source_context": "Discuss service models and tradeoffs.",
        },
    )
    assert "Your scope is strictly limited to the current slide text and speaker notes below." in prompt
    assert "I can only help with this slide." in prompt
