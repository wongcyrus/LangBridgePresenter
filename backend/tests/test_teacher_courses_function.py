import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def teacher_courses_module(monkeypatch):
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
    auth_mod.get_user = MagicMock()
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

    module_name = "teacher_courses_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/teacher-courses/main.py")
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


def test_teacher_courses_forbidden_for_non_teacher(teacher_courses_module, mock_request, monkeypatch):
    monkeypatch.setattr(teacher_courses_module, "_verify_user", lambda _request: {"uid": "u-1", "email": "u@example.com"})
    monkeypatch.setattr(teacher_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(teacher_courses_module, "_is_teacher", lambda _decoded, _db: False)
    teacher_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = teacher_courses_module.teacher_courses(mock_request)
    assert status == 403
    assert json.loads(body)["error"] == "Forbidden"


def test_teacher_courses_create_course(teacher_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "create_course", "title": "Intro Cloud", "languages": "en-US,zh-CN"}
    monkeypatch.setattr(teacher_courses_module, "_verify_user", lambda _request: {"uid": "t-1", "email": "t@example.com"})
    monkeypatch.setattr(teacher_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(teacher_courses_module, "_is_teacher", lambda _decoded, _db: True)

    db = MagicMock()
    courses_collection = MagicMock()
    course_ref = MagicMock()
    courses_collection.document.return_value = course_ref

    def _collection(name):
        if name == "courses":
            return courses_collection
        return MagicMock()

    db.collection.side_effect = _collection
    teacher_courses_module.firestore.Client.return_value = db

    body, status, _headers = teacher_courses_module.teacher_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert "course_id" in payload
    assert course_ref.set.called


def test_teacher_courses_set_student_status_allows_email_pending(teacher_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {
        "action": "set_student_status",
        "class_id": "class-1",
        "student_email": "student@example.com",
        "status": "active",
    }
    monkeypatch.setattr(teacher_courses_module, "_verify_user", lambda _request: {"uid": "t-1", "email": "t@example.com"})
    monkeypatch.setattr(teacher_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(teacher_courses_module, "_is_teacher", lambda _decoded, _db: True)

    class_doc = MagicMock()
    class_doc.exists = True
    class_doc.to_dict.return_value = {"teacher_uid": "t-1", "active": True}
    class_ref = MagicMock()
    class_ref.get.return_value = class_doc
    classes_collection = MagicMock()
    classes_collection.document.return_value = class_ref

    db = MagicMock()

    def _collection(name):
        if name == "classes":
            return classes_collection
        return MagicMock()

    db.collection.side_effect = _collection
    teacher_courses_module.firestore.Client.return_value = db
    teacher_courses_module.firebase_auth.get_user_by_email.side_effect = Exception("not found")
    set_email_mock = MagicMock()
    monkeypatch.setattr(teacher_courses_module, "_set_student_status_by_email", set_email_mock)
    monkeypatch.setattr(teacher_courses_module, "_set_student_status", MagicMock())

    body, status, _headers = teacher_courses_module.teacher_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["student_uid"] is None
    assert set_email_mock.called


def test_teacher_courses_set_student_status_uses_uid_when_auth_user_exists(teacher_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {
        "action": "set_student_status",
        "class_id": "class-1",
        "student_email": "student@example.com",
        "status": "active",
    }
    monkeypatch.setattr(teacher_courses_module, "_verify_user", lambda _request: {"uid": "t-1", "email": "t@example.com"})
    monkeypatch.setattr(teacher_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(teacher_courses_module, "_is_teacher", lambda _decoded, _db: True)
    teacher_courses_module.firebase_auth.get_user_by_email.return_value = types.SimpleNamespace(uid="student-uid")

    class_doc = MagicMock()
    class_doc.exists = True
    class_doc.to_dict.return_value = {"teacher_uid": "t-1", "active": True}
    class_ref = MagicMock()
    class_ref.get.return_value = class_doc
    classes_collection = MagicMock()
    classes_collection.document.return_value = class_ref

    db = MagicMock()

    def _collection(name):
        if name == "classes":
            return classes_collection
        return MagicMock()

    db.collection.side_effect = _collection
    teacher_courses_module.firestore.Client.return_value = db
    set_uid_mock = MagicMock()
    set_email_mock = MagicMock()
    monkeypatch.setattr(teacher_courses_module, "_set_student_status", set_uid_mock)
    monkeypatch.setattr(teacher_courses_module, "_set_student_status_by_email", set_email_mock)

    body, status, _headers = teacher_courses_module.teacher_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["student_uid"] == "student-uid"
    assert set_uid_mock.called
    assert not set_email_mock.called
