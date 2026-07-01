import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def voice_live_session_module(monkeypatch):
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

    module_name = "voice_live_session_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/voice-live-session/main.py")
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
    req.get_json.return_value = {"action": "open"}
    return req


def test_voice_live_session_rejects_unauthenticated(voice_live_session_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_live_session_module, "_verify_user", lambda _request: (_ for _ in ()).throw(PermissionError("bad"))
    )
    body, status, _headers = voice_live_session_module.voice_live_session(mock_request)
    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_voice_live_session_open_returns_lease(voice_live_session_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_live_session_module,
        "_verify_user",
        lambda _request: {"uid": "u-1", "email": "u1@example.com"},
    )
    monkeypatch.setattr(voice_live_session_module, "_has_voice_access", lambda _decoded, _db: True)

    db = MagicMock()
    lease_ref = MagicMock()
    lease_snap = MagicMock()
    lease_snap.exists = False
    lease_ref.get.return_value = lease_snap
    db.collection.return_value.document.return_value = lease_ref
    voice_live_session_module.firestore.Client.return_value = db

    body, status, _headers = voice_live_session_module.voice_live_session(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert "session_id" in payload
    assert lease_ref.set.called


def test_voice_live_session_heartbeat_rejects_invalid_session(voice_live_session_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {"action": "heartbeat", "session_id": "wrong"}
    monkeypatch.setattr(
        voice_live_session_module,
        "_verify_user",
        lambda _request: {"uid": "u-2", "email": "u2@example.com"},
    )
    monkeypatch.setattr(voice_live_session_module, "_has_voice_access", lambda _decoded, _db: True)

    db = MagicMock()
    lease_ref = MagicMock()
    lease_snap = MagicMock()
    lease_snap.exists = True
    lease_snap.to_dict.return_value = {
        "active": True,
        "session_id": "expected",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    lease_ref.get.return_value = lease_snap
    db.collection.return_value.document.return_value = lease_ref
    voice_live_session_module.firestore.Client.return_value = db

    body, status, _headers = voice_live_session_module.voice_live_session(mock_request)
    assert status == 403
    assert json.loads(body)["error"] == "Invalid voice session"


def test_voice_live_session_close_marks_inactive(voice_live_session_module, mock_request, monkeypatch):
    mock_request.get_json.return_value = {"action": "close", "session_id": "abc"}
    monkeypatch.setattr(
        voice_live_session_module,
        "_verify_user",
        lambda _request: {"uid": "u-3", "email": "u3@example.com"},
    )
    monkeypatch.setattr(voice_live_session_module, "_has_voice_access", lambda _decoded, _db: True)

    db = MagicMock()
    lease_ref = MagicMock()
    lease_snap = MagicMock()
    lease_snap.exists = True
    lease_snap.to_dict.return_value = {
        "active": True,
        "session_id": "abc",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    lease_ref.get.return_value = lease_snap
    db.collection.return_value.document.return_value = lease_ref
    voice_live_session_module.firestore.Client.return_value = db

    body, status, _headers = voice_live_session_module.voice_live_session(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["closed"] is True
    assert lease_ref.set.called
