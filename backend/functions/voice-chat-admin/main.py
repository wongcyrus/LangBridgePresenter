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
    # API Gateway forwards the caller auth header as X-Forwarded-Authorization
    # and uses Authorization for its own backend identity token.
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


def _default_limits():
    return {
        "minutes_per_day": int(os.environ.get("VOICE_LIVE_MINUTES_PER_DAY", "120")),
    }


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


def _voice_user_from_doc(doc):
    data = doc.to_dict() or {}
    doc_id = doc.id
    if ":" in doc_id:
        key_type, key_value = doc_id.split(":", 1)
    else:
        key_type, key_value = "unknown", doc_id
    return {
        "key": doc_id,
        "type": key_type,
        "value": key_value,
        "active": data.get("active") is True,
        "note": data.get("note"),
        "created_at": _to_iso8601(data.get("created_at")),
        "updated_at": _to_iso8601(data.get("updated_at")),
        "updated_by": data.get("updated_by"),
    }


def _list_voice_users(db: firestore.Client):
    users = []
    for doc in db.collection("voice_chat_users").stream():
        users.append(_voice_user_from_doc(doc))
    users.sort(
        key=lambda item: (
            item.get("active") is True,
            item.get("updated_at") or "",
            item.get("key") or "",
        ),
        reverse=True,
    )
    return users[:200]


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


@functions_framework.http
def voice_chat_admin(request: Request):
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
        logger.warning("voice_chat_admin auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)
    settings_ref = db.collection("voice_chat_settings").document("default")

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            if "minutes_per_day" in payload:
                action = "update_limits"
            else:
                return (json.dumps({"error": "action is required"}), 400, headers)

        if action == "update_limits":
            minutes_per_day_raw = payload.get("minutes_per_day")
            if minutes_per_day_raw is None and payload.get("requests_per_day") is not None:
                minutes_per_day_raw = payload.get("requests_per_day")
            if minutes_per_day_raw is None:
                return (json.dumps({"error": "minutes_per_day is required"}), 400, headers)
            try:
                minutes_per_day = int(minutes_per_day_raw)
            except (TypeError, ValueError):
                return (json.dumps({"error": "minutes_per_day must be an integer"}), 400, headers)
            if minutes_per_day <= 0:
                return (json.dumps({"error": "minutes_per_day must be > 0"}), 400, headers)
            if minutes_per_day > 24 * 60:
                return (json.dumps({"error": "minutes_per_day is too high"}), 400, headers)

            settings_ref.set(
                {
                    "minutes_per_day": minutes_per_day,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                    "updated_by": decoded.get("uid"),
                },
                merge=True,
            )
            return (
                json.dumps(
                    {
                        "ok": True,
                        "limits": {
                            "minutes_per_day": minutes_per_day,
                        },
                    }
                ),
                200,
                headers,
            )

        if action == "grant_voice_user":
            email = _normalize_email(str(payload.get("email") or ""))
            if not email or "@" not in email:
                return (json.dumps({"error": "Valid email is required"}), 400, headers)
            note = str(payload.get("note") or "").strip()
            user_ref = db.collection("voice_chat_users").document(f"email:{email}")
            existing_snap = user_ref.get()
            existing = existing_snap.to_dict() if existing_snap.exists else {}
            user_ref.set(
                {
                    "active": True,
                    "email": email,
                    "note": note if note else existing.get("note"),
                    "created_at": existing.get("created_at", firestore.SERVER_TIMESTAMP),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                    "updated_by": decoded.get("uid"),
                },
                merge=True,
            )
            return (json.dumps({"ok": True, "message": f"Granted voice access: {email}"}), 200, headers)

        if action == "revoke_voice_user":
            email = _normalize_email(str(payload.get("email") or ""))
            if not email or "@" not in email:
                return (json.dumps({"error": "Valid email is required"}), 400, headers)
            user_ref = db.collection("voice_chat_users").document(f"email:{email}")
            existing_snap = user_ref.get()
            if not existing_snap.exists:
                return (json.dumps({"error": "Voice user not found"}), 404, headers)
            user_ref.set(
                {
                    "active": False,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                    "updated_by": decoded.get("uid"),
                },
                merge=True,
            )
            return (json.dumps({"ok": True, "message": f"Revoked voice access: {email}"}), 200, headers)

        return (json.dumps({"error": f"Unsupported action: {action}"}), 400, headers)

    settings_snap = settings_ref.get()
    if settings_snap.exists:
        limits = settings_snap.to_dict()
    else:
        limits = _default_limits()

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
                "limits": {
                    "minutes_per_day": int(limits.get("minutes_per_day", _default_limits()["minutes_per_day"])),
                },
                "summary": {
                    "tracked_users": len(usage),
                    "total_today_minutes": round(total_today_seconds / 60, 2),
                },
                "top_usage": usage,
                "voice_users": _list_voice_users(db),
                "usage_logs": _list_usage_logs(db),
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
