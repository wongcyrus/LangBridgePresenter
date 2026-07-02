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


def _normalize_email(raw_value: str) -> str:
    return (raw_value or "").strip().lower()


def _teacher_doc_ref(db: firestore.Client, *, uid: str | None = None, email: str | None = None):
    normalized_email = _normalize_email(email or "")
    if uid:
        return db.collection("teacher_users").document(uid)
    if normalized_email:
        return db.collection("teacher_users").document(f"email:{normalized_email}")
    raise ValueError("uid or email is required")


def _teacher_from_doc(doc):
    data = doc.to_dict() or {}
    doc_id = doc.id
    principal_type = "uid"
    principal_value = doc_id
    if doc_id.startswith("email:"):
        principal_type = "email"
        principal_value = doc_id.split(":", 1)[1]
    return {
        "uid": data.get("uid"),
        "email": data.get("email"),
        "principal_type": principal_type,
        "principal_value": principal_value,
        "active": data.get("active") is True,
        "created_at": _to_iso8601(data.get("created_at")),
        "updated_at": _to_iso8601(data.get("updated_at")),
        "updated_by": data.get("updated_by"),
    }


def _list_teachers(db: firestore.Client):
    merged_by_principal = {}
    docs = db.collection("teacher_users").stream()
    for doc in docs:
        row = _teacher_from_doc(doc)
        dedupe_key = _normalize_email(row.get("email") or "") or (row.get("uid") or row.get("principal_value") or "")
        if not dedupe_key:
            continue
        existing = merged_by_principal.get(dedupe_key)
        if not existing:
            merged_by_principal[dedupe_key] = row
            continue

        existing_rank = (
            existing.get("active") is True,
            existing.get("principal_type") == "uid",
            existing.get("updated_at") or "",
        )
        next_rank = (
            row.get("active") is True,
            row.get("principal_type") == "uid",
            row.get("updated_at") or "",
        )
        if next_rank > existing_rank:
            merged_by_principal[dedupe_key] = row

    teachers = list(merged_by_principal.values())
    teachers.sort(
        key=lambda row: (
            row.get("active") is True,
            row.get("updated_at") or "",
            row.get("email") or "",
        ),
        reverse=True,
    )
    return teachers[:300]


@functions_framework.http
def admin_teachers(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method not in {"GET", "POST"}:
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    db = firestore.Client(database="langbridge")
    try:
        decoded = _verify_user(request)
        if not _is_admin(decoded, db):
            return (json.dumps({"error": "Forbidden"}), 403, headers)
    except Exception as e:
        logger.warning("admin_teachers auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    if request.method == "GET":
        return (json.dumps({"teachers": _list_teachers(db)}, ensure_ascii=False), 200, headers)

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"grant_teacher", "revoke_teacher"}:
        return (json.dumps({"error": "Unsupported action"}), 400, headers)

    email = _normalize_email(str(payload.get("email") or ""))
    if not email or "@" not in email:
        return (json.dumps({"error": "Valid email is required"}), 400, headers)

    active = action == "grant_teacher"
    teacher_ref = _teacher_doc_ref(db, email=email)
    existing_snap = teacher_ref.get()
    existing = existing_snap.to_dict() if existing_snap.exists else {}
    teacher_ref.set(
        {
            "email": email,
            "active": active,
            "created_at": existing.get("created_at", firestore.SERVER_TIMESTAMP),
            "updated_at": firestore.SERVER_TIMESTAMP,
            "updated_by": decoded.get("uid"),
        },
        merge=True,
    )

    resolved_uid = ""
    try:
        user = firebase_auth.get_user_by_email(email)
        resolved_uid = user.uid
    except Exception:
        resolved_uid = ""

    if resolved_uid:
        uid_ref = _teacher_doc_ref(db, uid=resolved_uid)
        uid_existing_snap = uid_ref.get()
        uid_existing = uid_existing_snap.to_dict() if uid_existing_snap.exists else {}
        uid_ref.set(
            {
                "uid": resolved_uid,
                "email": email,
                "active": active,
                "created_at": uid_existing.get("created_at", firestore.SERVER_TIMESTAMP),
                "updated_at": firestore.SERVER_TIMESTAMP,
                "updated_by": decoded.get("uid"),
            },
            merge=True,
        )

    return (
        json.dumps(
            {
                "ok": True,
                "uid": resolved_uid or None,
                "email": email,
                "active": active,
                "message": f"{'Granted' if active else 'Revoked'} teacher role: {email}",
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
