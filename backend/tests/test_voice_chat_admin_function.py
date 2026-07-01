import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def voice_chat_admin_module(monkeypatch):
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
    firestore_mod.Query = types.SimpleNamespace(DESCENDING="DESCENDING")
    firestore_mod.SERVER_TIMESTAMP = object()
    cloud_mod.firestore = firestore_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)

    module_name = "voice_chat_admin_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/voice-chat-admin/main.py")
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
    req.get_json.return_value = {}
    return req


def _setup_admin_get_db(module):
    db = MagicMock()
    settings_collection = MagicMock()
    users_collection = MagicMock()
    settings_ref = MagicMock()
    settings_snap = MagicMock()
    settings_snap.exists = True
    settings_snap.to_dict.return_value = {
        "minutes_per_day": 90,
    }
    settings_ref.get.return_value = settings_snap
    settings_collection.document.return_value = settings_ref

    user_doc = MagicMock()
    user_doc.id = "email:student@example.com"
    user_doc.to_dict.return_value = {
        "active": True,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    users_collection.stream.return_value = [user_doc]
    def _collection(name):
        if name == "voice_chat_settings":
            return settings_collection
        if name == "voice_chat_users":
            return users_collection
        raise AssertionError(f"Unexpected collection: {name}")

    db.collection.side_effect = _collection
    module.firestore.Client.return_value = db
    return db


def test_voice_chat_admin_rejects_unauthenticated(voice_chat_admin_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        voice_chat_admin_module, "_verify_user", lambda _request: (_ for _ in ()).throw(PermissionError("bad"))
    )

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)

    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_voice_chat_admin_get_returns_limits_and_users(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "GET"
    monkeypatch.setattr(voice_chat_admin_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})
    _setup_admin_get_db(voice_chat_admin_module)

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["limits"]["minutes_per_day"] == 90
    assert payload["summary"]["granted_users"] == 1
    assert payload["voice_users"][0]["key"] == "email:student@example.com"


def test_voice_chat_admin_post_updates_limits(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {
        "action": "update_limits",
        "minutes_per_day": 300,
    }
    monkeypatch.setattr(voice_chat_admin_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})

    db = MagicMock()
    settings_collection = MagicMock()
    settings_ref = MagicMock()
    settings_collection.document.return_value = settings_ref
    db.collection.return_value = settings_collection
    voice_chat_admin_module.firestore.Client.return_value = db

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["ok"] is True
    assert payload["limits"]["minutes_per_day"] == 300
    assert settings_ref.set.called


def test_voice_chat_admin_grants_voice_user(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "grant_voice_user", "email": "student@example.com"}
    monkeypatch.setattr(voice_chat_admin_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})

    db = MagicMock()
    users_collection = MagicMock()
    user_ref = MagicMock()
    user_snap = MagicMock()
    user_snap.exists = False
    user_ref.get.return_value = user_snap
    users_collection.document.return_value = user_ref

    settings_collection = MagicMock()
    settings_collection.document.return_value = MagicMock()

    def _collection(name):
        if name == "voice_chat_users":
            return users_collection
        if name == "voice_chat_settings":
            return settings_collection
        raise AssertionError(f"Unexpected collection: {name}")

    db.collection.side_effect = _collection
    voice_chat_admin_module.firestore.Client.return_value = db

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)
    assert status == 200
    payload = json.loads(body)
    assert payload["ok"] is True
    assert "Granted voice access" in payload["message"]
    assert user_ref.set.called


def test_voice_chat_admin_revokes_voice_user(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "revoke_voice_user", "email": "student@example.com"}
    monkeypatch.setattr(voice_chat_admin_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})

    db = MagicMock()
    users_collection = MagicMock()
    user_ref = MagicMock()
    user_snap = MagicMock()
    user_snap.exists = True
    user_ref.get.return_value = user_snap
    users_collection.document.return_value = user_ref

    settings_collection = MagicMock()
    settings_collection.document.return_value = MagicMock()

    def _collection(name):
        if name == "voice_chat_users":
            return users_collection
        if name == "voice_chat_settings":
            return settings_collection
        raise AssertionError(f"Unexpected collection: {name}")

    db.collection.side_effect = _collection
    voice_chat_admin_module.firestore.Client.return_value = db

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)
    assert status == 200
    payload = json.loads(body)
    assert payload["ok"] is True
    assert "Revoked voice access" in payload["message"]
    assert user_ref.set.called


def test_is_admin_via_firestore_uid_record(voice_chat_admin_module):
    db = MagicMock()
    admins_collection = MagicMock()
    uid_doc = MagicMock()
    uid_snap = MagicMock()
    uid_snap.exists = True
    uid_snap.to_dict.return_value = {"active": True}
    uid_doc.get.return_value = uid_snap
    admins_collection.document.return_value = uid_doc
    db.collection.return_value = admins_collection

    result = voice_chat_admin_module._is_admin({"uid": "u-123", "email": "nope@example.com"}, db)
    assert result is True


def test_extract_bearer_token_prefers_forwarded_header(voice_chat_admin_module, mock_request):
    mock_request.headers = {
        "Authorization": "Bearer gateway-token",
        "X-Forwarded-Authorization": "Bearer user-token",
    }
    token = voice_chat_admin_module._extract_bearer_token(mock_request)
    assert token == "user-token"
