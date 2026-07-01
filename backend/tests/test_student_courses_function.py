import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def student_courses_module(monkeypatch):
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
    firestore_mod.SERVER_TIMESTAMP = object()
    cloud_mod.firestore = firestore_mod
    google_mod.cloud = cloud_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", firestore_mod)

    module_name = "student_courses_main_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../functions/student-courses/main.py")
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


def test_student_courses_get_returns_classes(student_courses_module, mock_request, monkeypatch):
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "s-1", "email": "s@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: False)
    monkeypatch.setattr(
        student_courses_module,
        "_list_student_classes",
        lambda _db, uid, email: [{"class_id": "class-1", "title": "Class 1", "enrolled": True}],
    )
    student_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = student_courses_module.student_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["user"]["uid"] == "s-1"
    assert payload["classes"][0]["class_id"] == "class-1"


def test_student_courses_enroll(student_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "enroll", "class_id": "class-2"}
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "s-2", "email": "s2@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: False)
    enroll_mock = MagicMock()
    monkeypatch.setattr(student_courses_module, "_enroll_student", enroll_mock)
    student_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = student_courses_module.student_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert enroll_mock.called


def test_student_courses_current_view_denies_when_not_enrolled(student_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "current_view", "class_id": "class-2"}
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "s-2", "email": "s2@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: False)
    monkeypatch.setattr(
        student_courses_module,
        "_resolve_class_access",
        lambda _db, uid, email, class_id, is_admin: {"allowed": False, "role": "none", "class_data": {}},
    )
    view_mock = MagicMock()
    monkeypatch.setattr(student_courses_module, "_get_current_view", view_mock)
    student_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = student_courses_module.student_courses(mock_request)
    payload = json.loads(body)
    assert status == 403
    assert payload["error"] == "Class access denied"
    assert not view_mock.called


def test_student_courses_access_check_returns_role(student_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "access_check", "class_id": "class-3"}
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "t-1", "email": "t@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: True)
    monkeypatch.setattr(
        student_courses_module,
        "_resolve_class_access",
        lambda _db, uid, email, class_id, is_admin: {
            "allowed": True,
            "role": "teacher",
            "class_data": {"course_id": "course-1"},
        },
    )
    student_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = student_courses_module.student_courses(mock_request)
    payload = json.loads(body)
    assert status == 200
    assert payload["ok"] is True
    assert payload["allowed"] is True
    assert payload["role"] == "teacher"


def test_student_courses_get_passes_email_to_class_listing(student_courses_module, mock_request, monkeypatch):
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "s-5", "email": "s5@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: False)
    seen = {}

    def _list_classes(_db, uid, email):
        seen["uid"] = uid
        seen["email"] = email
        return []

    monkeypatch.setattr(student_courses_module, "_list_student_classes", _list_classes)
    student_courses_module.firestore.Client.return_value = MagicMock()

    _body, status, _headers = student_courses_module.student_courses(mock_request)
    assert status == 200
    assert seen["uid"] == "s-5"
    assert seen["email"] == "s5@example.com"


def test_student_courses_access_check_denied(student_courses_module, mock_request, monkeypatch):
    mock_request.method = "POST"
    mock_request.get_json.return_value = {"action": "access_check", "class_id": "class-8"}
    monkeypatch.setattr(student_courses_module, "_verify_user", lambda _request: {"uid": "s-8", "email": "s8@example.com"})
    monkeypatch.setattr(student_courses_module, "_is_admin", lambda _decoded, _db: False)
    monkeypatch.setattr(student_courses_module, "_is_teacher", lambda _decoded, _db: False)
    monkeypatch.setattr(
        student_courses_module,
        "_resolve_class_access",
        lambda _db, uid, email, class_id, is_admin: {"allowed": False, "role": "none", "class_data": {}},
    )
    student_courses_module.firestore.Client.return_value = MagicMock()

    body, status, _headers = student_courses_module.student_courses(mock_request)
    payload = json.loads(body)
    assert status == 403
    assert payload["error"] == "Class access denied"
