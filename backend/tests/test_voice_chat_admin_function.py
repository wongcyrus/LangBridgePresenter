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
    usage_collection = MagicMock()
    settings_ref = MagicMock()
    settings_snap = MagicMock()
    settings_snap.exists = True
    settings_snap.to_dict.return_value = {
        "requests_per_minute": 15,
        "requests_per_day": 500,
    }
    settings_ref.get.return_value = settings_snap
    settings_collection.document.return_value = settings_ref

    usage_doc = MagicMock()
    usage_doc.id = "user-1"
    usage_doc.to_dict.return_value = {
        "day_key": "20990101",
        "day_count": 42,
        "minute_key": "209901010101",
        "minute_count": 2,
    }
    usage_query = MagicMock()
    usage_query.limit.return_value.stream.return_value = [usage_doc]
    usage_collection.order_by.return_value = usage_query

    def _collection(name):
        if name == "voice_chat_settings":
            return settings_collection
        if name == "voice_chat_usage":
            return usage_collection
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


def test_voice_chat_admin_get_returns_limits_and_usage(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "GET"
    monkeypatch.setattr(voice_chat_admin_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})
    _setup_admin_get_db(voice_chat_admin_module)

    body, status, _headers = voice_chat_admin_module.voice_chat_admin(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["limits"]["requests_per_minute"] == 15
    assert payload["limits"]["requests_per_day"] == 500
    assert payload["summary"]["tracked_users"] == 1
    assert payload["top_usage"][0]["uid"] == "user-1"


def test_voice_chat_admin_post_updates_limits(voice_chat_admin_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"requests_per_minute": 12, "requests_per_day": 300}
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
    assert payload["limits"]["requests_per_minute"] == 12
    assert payload["limits"]["requests_per_day"] == 300
    assert settings_ref.set.called


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
