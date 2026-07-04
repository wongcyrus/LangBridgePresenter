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
    tts_mod.SsmlVoiceGender = types.SimpleNamespace(FEMALE="FEMALE", MALE="MALE")
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
    assert "Decide first whether the question is related to the current slide topic/content." in prompt
    assert "I can only help with this slide." in prompt
    assert "Recent conversation (oldest to newest):" in prompt


def test_extract_citations_from_response_dict(tutor_ask_module):
    class DummyResponse:
        def to_dict(self):
            return {
                "grounding_metadata": {
                    "supports": [{"source_uri": "https://example.com/news-a"}],
                    "chunks": [{"url": "https://example.com/news-b"}],
                }
            }

    links = tutor_ask_module._extract_citations(DummyResponse(), max_items=5)
    assert links == ["https://example.com/news-a", "https://example.com/news-b"]


def test_normalize_chat_history_keeps_recent_turns(tutor_ask_module):
    raw_history = [
        {"role": "system", "text": "ignore"},
        {"role": "user", "text": "What is SaaS?"},
        {"role": "assistant", "text": "Software as a service."},
        {"role": "user", "text": "x" * 400},
        {"role": "assistant", "text": ""},
    ]
    turns = tutor_ask_module._normalize_chat_history(raw_history, max_turns=4, max_chars=40)
    assert len(turns) == 3
    assert turns[0] == {"role": "user", "text": "What is SaaS?"}
    assert turns[1] == {"role": "assistant", "text": "Software as a service."}
    assert turns[2]["role"] == "user"
    assert len(turns[2]["text"]) == 40


def test_resolve_tts_profile_for_chitose_and_wild(tutor_ask_module):
    chitose = tutor_ask_module._resolve_tts_profile("Chitose")
    assert chitose["gender"] == "MALE"
    assert float(chitose["speaking_rate"]) == 1.0

    wild = tutor_ask_module._resolve_tts_profile("Wild")
    assert wild["gender"] == "MALE"
    assert float(wild["speaking_rate"]) == 0.92
    assert float(wild["pitch"]) == -2.0


def test_resolve_tts_profile_defaults_to_female(tutor_ask_module):
    profile = tutor_ask_module._resolve_tts_profile("UnknownAvatar")
    assert profile["gender"] == "FEMALE"
    assert float(profile["speaking_rate"]) == 1.0
