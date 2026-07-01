import json
import logging
import os
import sys
from datetime import datetime, timezone

import firebase_admin
import functions_framework
from firebase_admin import auth as firebase_auth
from flask import Request
from google.cloud import firestore


_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)
_root = logging.getLogger()
_root.setLevel(_level)
if not any(isinstance(h, logging.StreamHandler) for h in _root.handlers):
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter("%(levelname)s:%(name)s:%(asctime)s:%(message)s")
    _handler.setFormatter(_formatter)
    _handler.setLevel(_level)
    _root.addHandler(_handler)
logger = logging.getLogger(__name__)
logger.setLevel(_level)


if not firebase_admin._apps:
    firebase_project_id = os.environ.get("CLIENT_FIREBASE_PROJECT_ID") or os.environ.get("CLIENT_FIRESTORE_PROJECT_ID")
    if firebase_project_id:
        firebase_admin.initialize_app(options={"projectId": firebase_project_id})
    else:
        firebase_admin.initialize_app()


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Content-Type": "application/json",
    }


def _extract_bearer_token(request: Request) -> str:
    forwarded_auth = request.headers.get("X-Forwarded-Authorization", "")
    if forwarded_auth.startswith("Bearer "):
        return forwarded_auth.split(" ", 1)[1].strip()

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return ""


def _verify_user(request: Request):
    token = _extract_bearer_token(request)
    if not token:
        raise PermissionError("Missing bearer token")
    return firebase_auth.verify_id_token(token)


def _normalize_email(raw_value: str) -> str:
    return (raw_value or "").strip().lower()


def _is_admin(decoded_token: dict, db: firestore.Client) -> bool:
    if decoded_token.get("admin") is True:
        return True
    allowlist = os.environ.get("VOICE_CHAT_ADMIN_EMAILS", "").strip()
    email = (decoded_token.get("email") or "").lower()
    if allowlist:
        allowed = {e.strip().lower() for e in allowlist.split(",") if e.strip()}
        if email in allowed:
            return True

    uid = decoded_token.get("uid")
    if uid:
        snap = db.collection("admin_users").document(f"uid:{uid}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    if email:
        snap = db.collection("admin_users").document(f"email:{email}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    return False


def _is_teacher(decoded_token: dict, db: firestore.Client) -> bool:
    uid = decoded_token.get("uid")
    email = _normalize_email(decoded_token.get("email") or "")
    if uid:
        teacher_snap = db.collection("teacher_users").document(uid).get()
        if teacher_snap.exists and (teacher_snap.to_dict() or {}).get("active") is True:
            return True
    if email:
        teacher_email_snap = db.collection("teacher_users").document(f"email:{email}").get()
        if teacher_email_snap.exists and (teacher_email_snap.to_dict() or {}).get("active") is True:
            return True
    return False


def _to_iso8601(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _list_student_classes(db: firestore.Client, *, uid: str, email: str):
    enrollment_map = {}
    for enrollment_doc in db.collection("student_enrollments").document(uid).collection("classes").stream():
        enrollment_map[enrollment_doc.id] = enrollment_doc.to_dict() or {}
    if email:
        email_principal = f"email:{_normalize_email(email)}"
        for enrollment_doc in db.collection("student_enrollments").document(email_principal).collection("classes").stream():
            if enrollment_doc.id not in enrollment_map:
                enrollment_map[enrollment_doc.id] = enrollment_doc.to_dict() or {}

    classes = []
    for class_doc in db.collection("classes").where("active", "==", True).stream():
        class_data = class_doc.to_dict() or {}
        class_id = class_data.get("class_id") or class_doc.id
        course_id = class_data.get("course_id")
        course_title = None
        if course_id:
            course_snap = db.collection("courses").document(course_id).get()
            if course_snap.exists:
                course_title = (course_snap.to_dict() or {}).get("title")
        enrollment = enrollment_map.get(class_id) or {}
        classes.append(
            {
                "class_id": class_id,
                "title": class_data.get("title"),
                "course_id": course_id,
                "course_title": course_title,
                "teacher_uid": class_data.get("teacher_uid"),
                "teacher_email": class_data.get("teacher_email"),
                "is_public": class_data.get("is_public") is True,
                "current_presentation_id": class_data.get("current_presentation_id"),
                "current_slide_id": class_data.get("current_slide_id"),
                "enrolled": (enrollment.get("active") is True) or (class_data.get("is_public") is True),
                "student_status": enrollment.get("status"),
                "updated_at": _to_iso8601(class_data.get("updated_at")),
            }
        )
    classes.sort(key=lambda row: (row.get("enrolled") is True, row.get("updated_at") or "", row.get("title") or ""), reverse=True)
    return classes[:500]


def _enroll_student(db: firestore.Client, *, uid: str, email: str, class_id: str):
    class_ref = db.collection("classes").document(class_id)
    class_snap = class_ref.get()
    if not class_snap.exists:
        raise ValueError("Class not found")
    class_data = class_snap.to_dict() or {}
    if class_data.get("active") is False:
        raise ValueError("Class is inactive")

    now = firestore.SERVER_TIMESTAMP
    class_ref.collection("students").document(uid).set(
        {
            "uid": uid,
            "email": email,
            "status": "active",
            "active": True,
            "updated_at": now,
        },
        merge=True,
    )
    db.collection("student_enrollments").document(uid).collection("classes").document(class_id).set(
        {
            "class_id": class_id,
            "status": "active",
            "active": True,
            "updated_at": now,
        },
        merge=True,
    )


def _get_current_view(db: firestore.Client, *, class_id: str):
    class_snap = db.collection("classes").document(class_id).get()
    if not class_snap.exists:
        raise ValueError("Class not found")
    class_data = class_snap.to_dict() or {}
    if class_data.get("active") is False:
        raise ValueError("Class is inactive")

    broadcast_snap = db.collection("presentation_broadcast").document(class_id).get()
    if not broadcast_snap.exists:
        raise ValueError("Class presentation view not found")
    broadcast_data = broadcast_snap.to_dict() or {}
    return {
        "class_id": class_id,
        "current_presentation_id": broadcast_data.get("current_presentation_id"),
        "current_slide_id": broadcast_data.get("current_slide_id"),
        "latest_languages": broadcast_data.get("latest_languages") or {},
        "broadcast_status": broadcast_data.get("broadcast_status") or {},
    }


def _promote_email_enrollment_to_uid(db: firestore.Client, *, uid: str, email: str, class_id: str):
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return False
    principal_id = f"email:{normalized_email}"
    class_email_student_ref = db.collection("classes").document(class_id).collection("students").document(principal_id)
    class_email_student_snap = class_email_student_ref.get()
    enrollment_email_ref = db.collection("student_enrollments").document(principal_id).collection("classes").document(class_id)
    enrollment_email_snap = enrollment_email_ref.get()
    email_student_data = class_email_student_snap.to_dict() if class_email_student_snap.exists else {}
    email_enrollment_data = enrollment_email_snap.to_dict() if enrollment_email_snap.exists else {}
    if not class_email_student_snap.exists and not enrollment_email_snap.exists:
        return False

    active = (email_student_data.get("active") is True) or (email_enrollment_data.get("active") is True)
    status = email_student_data.get("status") or email_enrollment_data.get("status") or "active"
    now = firestore.SERVER_TIMESTAMP
    db.collection("classes").document(class_id).collection("students").document(uid).set(
        {
            "uid": uid,
            "email": normalized_email,
            "status": status,
            "active": active,
            "updated_at": now,
            "updated_by": uid,
            "linked_principal": principal_id,
        },
        merge=True,
    )
    db.collection("student_enrollments").document(uid).collection("classes").document(class_id).set(
        {
            "class_id": class_id,
            "status": status,
            "active": active,
            "updated_at": now,
            "updated_by": uid,
            "linked_principal": principal_id,
            "email": normalized_email,
        },
        merge=True,
    )
    return active


def _resolve_class_access(db: firestore.Client, *, uid: str, email: str, class_id: str, is_admin: bool):
    class_snap = db.collection("classes").document(class_id).get()
    if not class_snap.exists:
        raise ValueError("Class not found")
    class_data = class_snap.to_dict() or {}
    if class_data.get("active") is False:
        raise ValueError("Class is inactive")

    if is_admin:
        return {"allowed": True, "role": "admin", "class_data": class_data}
    if class_data.get("teacher_uid") == uid:
        return {"allowed": True, "role": "teacher", "class_data": class_data}
    if class_data.get("is_public") is True:
        return {"allowed": True, "role": "public", "class_data": class_data}

    enrollment = db.collection("student_enrollments").document(uid).collection("classes").document(class_id).get()
    if enrollment.exists and (enrollment.to_dict() or {}).get("active") is True:
        return {"allowed": True, "role": "student", "class_data": class_data}

    class_student = db.collection("classes").document(class_id).collection("students").document(uid).get()
    if class_student.exists and (class_student.to_dict() or {}).get("active") is True:
        return {"allowed": True, "role": "student", "class_data": class_data}

    if _promote_email_enrollment_to_uid(db, uid=uid, email=email, class_id=class_id):
        return {"allowed": True, "role": "student", "class_data": class_data}

    return {"allowed": False, "role": "none", "class_data": class_data}


@functions_framework.http
def student_courses(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method not in {"GET", "POST"}:
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    db = firestore.Client(database="langbridge")
    try:
        decoded = _verify_user(request)
    except Exception as e:
        logger.warning("student_courses auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    uid = decoded.get("uid")
    email = _normalize_email(decoded.get("email") or "")
    if not uid:
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    is_admin = _is_admin(decoded, db)
    is_teacher = _is_teacher(decoded, db)

    if request.method == "GET":
        return (
            json.dumps(
                {
                    "user": {
                        "uid": uid,
                        "email": email,
                        "is_admin": is_admin,
                        "is_teacher": is_teacher or is_admin,
                    },
                    "classes": _list_student_classes(db, uid=uid, email=email),
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip().lower()
    class_id = str(payload.get("class_id") or "").strip()
    if not class_id:
        return (json.dumps({"error": "class_id is required"}), 400, headers)

    if action == "enroll":
        try:
            _enroll_student(db, uid=uid, email=email, class_id=class_id)
        except ValueError as e:
            return (json.dumps({"error": str(e)}), 400, headers)
        return (json.dumps({"ok": True, "class_id": class_id}, ensure_ascii=False), 200, headers)

    if action == "access_check":
        try:
            access = _resolve_class_access(db, uid=uid, email=email, class_id=class_id, is_admin=is_admin)
        except ValueError as e:
            return (json.dumps({"error": str(e)}), 400, headers)
        if not access.get("allowed"):
            return (json.dumps({"error": "Class access denied", "role": "none"}), 403, headers)
        class_data = access.get("class_data") or {}
        return (
            json.dumps(
                {
                    "ok": True,
                    "allowed": True,
                    "role": access.get("role"),
                    "class_id": class_id,
                    "course_id": class_data.get("course_id"),
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    if action == "current_view":
        try:
            access = _resolve_class_access(db, uid=uid, email=email, class_id=class_id, is_admin=is_admin)
            if not access.get("allowed"):
                return (json.dumps({"error": "Class access denied"}), 403, headers)
            view_payload = _get_current_view(db, class_id=class_id)
        except ValueError as e:
            return (json.dumps({"error": str(e)}), 400, headers)
        return (json.dumps({"ok": True, "role": access.get("role"), **view_payload}, ensure_ascii=False), 200, headers)

    return (json.dumps({"error": f"Unsupported action: {action}"}), 400, headers)
