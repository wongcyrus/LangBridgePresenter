import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def teacher_student_records_module(monkeypatch):
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
    cloud_mod.firestore = firestore_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)

    module_name = "teacher_student_records_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/teacher-student-records/main.py")
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


def _setup_teacher_records_db(module):
    db = MagicMock()
    usage_collection = MagicMock()
    usage_logs_collection = MagicMock()
    user_settings_collection = MagicMock()

    usage_doc = MagicMock()
    usage_doc.id = "user-1:20990101"
    usage_doc.to_dict.return_value = {
        "uid": "user-1",
        "email": "user-1@example.com",
        "day_key": "20990101",
        "used_seconds": 3660,
    }
    usage_collection.where.return_value.stream.return_value = [usage_doc]

    usage_log_doc = MagicMock()
    usage_log_doc.id = "user-1:session-a"
    usage_log_doc.to_dict.return_value = {
        "uid": "user-1",
        "email": "user-1@example.com",
        "session_id": "session-a",
        "day_key": "20990101",
        "duration_seconds": 180,
        "ended_reason": "client_stop",
        "started_at": "2099-01-01T00:00:00Z",
        "ended_at": "2099-01-01T00:03:00Z",
    }
    usage_logs_collection.order_by.return_value.limit.return_value.stream.return_value = [usage_log_doc]

    settings_doc = MagicMock()
    settings_doc.id = "user-1"
    settings_doc.to_dict.return_value = {
        "uid": "user-1",
        "email": "user-1@example.com",
        "display_language": "en-US",
        "audio_language": "yue-HK",
        "autoplay": True,
        "presentation_id": "deck-1",
        "updated_at": "2099-01-01T00:10:00Z",
    }
    user_settings_collection.order_by.return_value.limit.return_value.stream.return_value = [settings_doc]

    def _collection(name):
        if name == "voice_live_usage_daily":
            return usage_collection
        if name == "voice_live_usage_logs":
            return usage_logs_collection
        if name == "voice_user_settings":
            return user_settings_collection
        if name == "admin_users":
            admins = MagicMock()
            admin_doc = MagicMock()
            admin_snap = MagicMock()
            admin_snap.exists = True
            admin_snap.to_dict.return_value = {"active": True}
            admin_doc.get.return_value = admin_snap
            admins.document.return_value = admin_doc
            return admins
        raise AssertionError(f"Unexpected collection: {name}")

    db.collection.side_effect = _collection
    module.firestore.Client.return_value = db


def test_teacher_student_records_rejects_unauthenticated(teacher_student_records_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        teacher_student_records_module, "_verify_user", lambda _request: (_ for _ in ()).throw(PermissionError("bad"))
    )

    body, status, _headers = teacher_student_records_module.teacher_student_records(mock_request)

    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_teacher_student_records_returns_usage_and_settings(teacher_student_records_module, mock_request, monkeypatch):
    monkeypatch.setattr(
        teacher_student_records_module,
        "_verify_user",
        lambda _request: {"uid": "admin-1", "email": "admin@example.com"},
    )
    monkeypatch.setattr(teacher_student_records_module, "_is_admin", lambda _decoded, _db: True)
    _setup_teacher_records_db(teacher_student_records_module)

    body, status, _headers = teacher_student_records_module.teacher_student_records(mock_request)

    assert status == 200
    payload = json.loads(body)
    assert payload["summary"]["tracked_users"] == 1
    assert payload["summary"]["total_today_minutes"] == 61.0
    assert payload["top_usage"][0]["uid"] == "user-1"
    assert payload["usage_logs"][0]["session_id"] == "session-a"
    assert payload["user_settings"][0]["audio_language"] == "yue-HK"
