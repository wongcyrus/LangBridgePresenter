import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def voice_chat_access_module(monkeypatch):
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
    cloud_mod = types.ModuleType("google.cloud")
    cloud_mod.__path__ = []
    firestore_mod = types.ModuleType("google.cloud.firestore")
    firestore_mod.Client = MagicMock()
    cloud_mod.firestore = firestore_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)

    module_name = "voice_chat_access_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/voice-chat-access/main.py")
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
    req.method = "GET"
    return req


def test_voice_chat_access_rejects_unauthenticated(voice_chat_access_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_access_module, "_verify_user", lambda _request: (_ for _ in ()).throw(PermissionError("bad"))
    )

    body, status, _headers = voice_chat_access_module.voice_chat_access(mock_request)

    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_voice_chat_access_returns_granted(voice_chat_access_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_access_module,
        "_verify_user",
        lambda _request: {"uid": "u-1", "email": "u1@example.com"},
    )
    monkeypatch.setattr(voice_chat_access_module, "_has_voice_access", lambda _decoded, _db: True)
    voice_chat_access_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = voice_chat_access_module.voice_chat_access(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["granted"] is True
    assert payload["uid"] == "u-1"


def test_voice_chat_access_returns_not_granted(voice_chat_access_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_access_module,
        "_verify_user",
        lambda _request: {"uid": "u-2", "email": "u2@example.com"},
    )
    monkeypatch.setattr(voice_chat_access_module, "_has_voice_access", lambda _decoded, _db: False)
    voice_chat_access_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = voice_chat_access_module.voice_chat_access(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["granted"] is False
    assert payload["reason"] == "Voice chat access requires admin grant"


def test_extract_bearer_token_prefers_forwarded_header(voice_chat_access_module, mock_request):
    mock_request.headers = {
        "Authorization": "Bearer gateway-token",
        "X-Forwarded-Authorization": "Bearer user-token",
    }
    token = voice_chat_access_module._extract_bearer_token(mock_request)
    assert token == "user-token"
