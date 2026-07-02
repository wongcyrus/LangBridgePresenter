import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def admin_teachers_module(monkeypatch):
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
    auth_mod.get_user_by_email = MagicMock()
    mock_firebase_admin.auth = auth_mod
    monkeypatch.setitem(sys.modules, "firebase_admin", mock_firebase_admin)
    monkeypatch.setitem(sys.modules, "firebase_admin.auth", auth_mod)

    google_mod = types.ModuleType("google")
    google_mod.__path__ = []
    cloud_mod = types.ModuleType("google.cloud")
    cloud_mod.__path__ = []
    firestore_mod = types.ModuleType("google.cloud.firestore")
    firestore_mod.Client = MagicMock()
    firestore_mod.SERVER_TIMESTAMP = object()
    cloud_mod.firestore = firestore_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)

    module_name = "admin_teachers_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/admin-teachers/main.py")
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


def test_admin_teachers_rejects_unauthenticated(admin_teachers_module, mock_request, monkeypatch):
    monkeypatch.setattr(admin_teachers_module, "_verify_user", lambda _request: (_ for _ in ()).throw(PermissionError("bad")))
    body, status, _headers = admin_teachers_module.admin_teachers(mock_request)
    assert status == 401
    assert json.loads(body)["error"] == "Unauthorized"


def test_admin_teachers_grant_teacher(admin_teachers_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "grant_teacher", "email": "teacher@example.com"}
    monkeypatch.setattr(admin_teachers_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})

    db = MagicMock()
    teachers_collection = MagicMock()
    teacher_ref = MagicMock()
    teacher_snap = MagicMock()
    teacher_snap.exists = False
    teacher_ref.get.return_value = teacher_snap
    teachers_collection.document.return_value = teacher_ref

    db.collection.return_value = teachers_collection
    admin_teachers_module.firestore.Client.return_value = db
    admin_teachers_module.firebase_auth.get_user_by_email.return_value = types.SimpleNamespace(uid="teacher-uid")

    body, status, _headers = admin_teachers_module.admin_teachers(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["active"] is True
    assert teacher_ref.set.called


def test_admin_teachers_grant_teacher_without_existing_auth_user(admin_teachers_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "grant_teacher", "email": "newteacher@example.com"}
    monkeypatch.setattr(admin_teachers_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})

    db = MagicMock()
    teachers_collection = MagicMock()
    teacher_ref = MagicMock()
    teacher_snap = MagicMock()
    teacher_snap.exists = False
    teacher_ref.get.return_value = teacher_snap
    teachers_collection.document.return_value = teacher_ref
    db.collection.return_value = teachers_collection
    admin_teachers_module.firestore.Client.return_value = db
    admin_teachers_module.firebase_auth.get_user_by_email.side_effect = Exception("not found")

    body, status, _headers = admin_teachers_module.admin_teachers(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["uid"] is None
    assert payload["email"] == "newteacher@example.com"


def test_admin_teachers_grant_teacher_writes_uid_mirror_when_user_exists(admin_teachers_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "grant_teacher", "email": "teacher@example.com"}
    monkeypatch.setattr(admin_teachers_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})
    admin_teachers_module.firebase_auth.get_user_by_email.return_value = types.SimpleNamespace(uid="teacher-uid")

    db = MagicMock()
    teachers_collection = MagicMock()
    refs = {}

    def _document(doc_id):
        ref = refs.get(doc_id)
        if ref is None:
            ref = MagicMock()
            snap = MagicMock()
            snap.exists = False
            snap.to_dict.return_value = {}
            ref.get.return_value = snap
            refs[doc_id] = ref
        return ref

    teachers_collection.document.side_effect = _document
    db.collection.return_value = teachers_collection
    admin_teachers_module.firestore.Client.return_value = db

    body, status, _headers = admin_teachers_module.admin_teachers(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["uid"] == "teacher-uid"
    assert refs["email:teacher@example.com"].set.called
    assert refs["teacher-uid"].set.called


def test_admin_teachers_revoke_teacher_works_without_existing_auth_user(admin_teachers_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "revoke_teacher", "email": "oldteacher@example.com"}
    monkeypatch.setattr(admin_teachers_module, "_verify_user", lambda _request: {"uid": "admin-1", "admin": True})
    admin_teachers_module.firebase_auth.get_user_by_email.side_effect = Exception("not found")

    db = MagicMock()
    teachers_collection = MagicMock()
    teacher_ref = MagicMock()
    teacher_snap = MagicMock()
    teacher_snap.exists = True
    teacher_snap.to_dict.return_value = {"active": True}
    teacher_ref.get.return_value = teacher_snap
    teachers_collection.document.return_value = teacher_ref
    db.collection.return_value = teachers_collection
    admin_teachers_module.firestore.Client.return_value = db

    body, status, _headers = admin_teachers_module.admin_teachers(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["active"] is False


def test_list_teachers_deduplicates_email_and_uid_mirror(admin_teachers_module):
    db = MagicMock()
    teachers_collection = MagicMock()
    db.collection.return_value = teachers_collection

    email_doc = MagicMock()
    email_doc.id = "email:teacher@example.com"
    email_doc.to_dict.return_value = {
        "email": "teacher@example.com",
        "active": True,
        "updated_at": "2026-07-01T10:00:00+00:00",
    }
    uid_doc = MagicMock()
    uid_doc.id = "teacher-uid"
    uid_doc.to_dict.return_value = {
        "uid": "teacher-uid",
        "email": "teacher@example.com",
        "active": True,
        "updated_at": "2026-07-01T10:00:00+00:00",
    }

    teachers_collection.stream.return_value = [email_doc, uid_doc]

    teachers = admin_teachers_module._list_teachers(db)
    assert len(teachers) == 1
    assert teachers[0]["email"] == "teacher@example.com"
    assert teachers[0]["uid"] == "teacher-uid"
