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
        "Access-Control-Allow-Methods": "GET, OPTIONS",
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


def _list_usage_logs(db: firestore.Client):
    logs = []
    docs = db.collection("voice_live_usage_logs").order_by("ended_at", direction=firestore.Query.DESCENDING).limit(50).stream()
    for doc in docs:
        data = doc.to_dict() or {}
        logs.append(
            {
                "id": doc.id,
                "uid": data.get("uid"),
                "email": data.get("email"),
                "session_id": data.get("session_id"),
                "day_key": data.get("day_key"),
                "duration_seconds": int(data.get("duration_seconds", 0)),
                "ended_reason": data.get("ended_reason"),
                "started_at": data.get("started_at"),
                "ended_at": data.get("ended_at"),
            }
        )
    return logs


def _user_settings_from_doc(doc):
    data = doc.to_dict() or {}
    return {
        "uid": data.get("uid") or doc.id,
        "email": data.get("email"),
        "display_language": data.get("display_language"),
        "audio_language": data.get("audio_language"),
        "autoplay": data.get("autoplay"),
        "course_id": data.get("course_id"),
        "presentation_id": data.get("presentation_id"),
        "slide_id": data.get("slide_id"),
        "last_session_id": data.get("last_session_id"),
        "updated_at": _to_iso8601(data.get("updated_at")),
    }


def _list_user_settings(db: firestore.Client):
    settings = []
    docs = db.collection("voice_user_settings").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(200).stream()
    for doc in docs:
        settings.append(_user_settings_from_doc(doc))
    return settings


@functions_framework.http
def teacher_student_records(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method != "GET":
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    db = firestore.Client(database="langbridge")

    try:
        decoded = _verify_user(request)
        if not _is_admin(decoded, db):
            return (json.dumps({"error": "Forbidden"}), 403, headers)
    except Exception as e:
        logger.warning("teacher_student_records auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    usage = []
    total_today_seconds = 0
    today_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    usage_docs = db.collection("voice_live_usage_daily").where("day_key", "==", today_key).stream()
    for doc in usage_docs:
        data = doc.to_dict() or {}
        used_seconds = int(data.get("used_seconds", 0))
        total_today_seconds += used_seconds
        usage.append(
            {
                "uid": data.get("uid") or (doc.id.split(":")[0] if ":" in doc.id else doc.id),
                "email": data.get("email"),
                "day_key": data.get("day_key"),
                "used_seconds": used_seconds,
                "used_minutes": round(used_seconds / 60, 2),
            }
        )
    usage.sort(key=lambda row: row.get("used_seconds", 0), reverse=True)
    usage = usage[:50]

    return (
        json.dumps(
            {
                "summary": {
                    "tracked_users": len(usage),
                    "total_today_minutes": round(total_today_seconds / 60, 2),
                },
                "top_usage": usage,
                "usage_logs": _list_usage_logs(db),
                "user_settings": _list_user_settings(db),
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
