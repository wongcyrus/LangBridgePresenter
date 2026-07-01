import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

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
        "Access-Control-Allow-Methods": "POST, OPTIONS",
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


def _has_voice_access(decoded_token: dict, db: firestore.Client) -> bool:
    uid = decoded_token.get("uid")
    email = (decoded_token.get("email") or "").strip().lower()

    if uid:
        snap = db.collection("voice_chat_users").document(f"uid:{uid}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    if email:
        snap = db.collection("voice_chat_users").document(f"email:{email}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    return False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso8601_z(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso8601(ts: str) -> datetime:
    normalized = (ts or "").replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _session_limits():
    max_seconds = int(os.environ.get("VOICE_LIVE_MAX_SESSION_SECONDS", "3600"))
    heartbeat_seconds = int(os.environ.get("VOICE_LIVE_HEARTBEAT_SECONDS", "30"))
    if max_seconds < 60:
        max_seconds = 60
    if heartbeat_seconds < 10:
        heartbeat_seconds = 10
    return max_seconds, heartbeat_seconds


def _deny(message: str, status_code: int, headers: dict):
    return (json.dumps({"error": message}, ensure_ascii=False), status_code, headers)


@functions_framework.http
def voice_live_session(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method != "POST":
        return _deny("Method not allowed", 405, headers)

    try:
        decoded = _verify_user(request)
    except Exception as e:
        logger.warning("voice_live_session auth failed: %s", e)
        return _deny("Unauthorized", 401, headers)

    uid = decoded.get("uid")
    if not uid:
        return _deny("Unauthorized", 401, headers)

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"open", "heartbeat", "close"}:
        return _deny("action must be open, heartbeat, or close", 400, headers)

    db = firestore.Client(database="langbridge")
    if not _has_voice_access(decoded, db):
        return _deny("Voice chat access requires admin grant", 403, headers)

    now = _utc_now()
    max_session_seconds, heartbeat_seconds = _session_limits()
    lease_ref = db.collection("voice_live_sessions").document(uid)
    lease_snap = lease_ref.get()
    lease = lease_snap.to_dict() if lease_snap.exists else {}

    if action == "open":
        session_id = secrets.token_urlsafe(18)
        expires_at = now + timedelta(seconds=max_session_seconds)
        lease_ref.set(
            {
                "uid": uid,
                "email": (decoded.get("email") or "").strip().lower(),
                "session_id": session_id,
                "active": True,
                "created_at": _iso8601_z(now),
                "updated_at": _iso8601_z(now),
                "last_heartbeat_at": _iso8601_z(now),
                "expires_at": _iso8601_z(expires_at),
                "max_session_seconds": max_session_seconds,
                "heartbeat_seconds": heartbeat_seconds,
                "course_id": payload.get("course_id") or payload.get("courseId"),
                "presentation_id": payload.get("presentation_id") or payload.get("presentationId"),
                "slide_id": str(payload.get("slide_id") or payload.get("slideId") or ""),
            },
            merge=True,
        )
        return (
            json.dumps(
                {
                    "ok": True,
                    "session_id": session_id,
                    "expires_at": _iso8601_z(expires_at),
                    "heartbeat_interval_seconds": heartbeat_seconds,
                    "max_session_seconds": max_session_seconds,
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    session_id = str(payload.get("session_id") or payload.get("sessionId") or "").strip()
    if not lease or lease.get("active") is not True:
        return _deny("No active voice session", 403, headers)
    if not session_id or session_id != lease.get("session_id"):
        return _deny("Invalid voice session", 403, headers)

    expires_at_raw = lease.get("expires_at")
    if not expires_at_raw:
        lease_ref.set({"active": False, "updated_at": _iso8601_z(now), "ended_reason": "lease_missing_expiry"}, merge=True)
        return _deny("Voice session expired", 403, headers)

    try:
        expires_at = _parse_iso8601(expires_at_raw)
    except Exception:
        lease_ref.set({"active": False, "updated_at": _iso8601_z(now), "ended_reason": "lease_invalid_expiry"}, merge=True)
        return _deny("Voice session expired", 403, headers)

    if now >= expires_at:
        lease_ref.set({"active": False, "updated_at": _iso8601_z(now), "ended_reason": "lease_expired"}, merge=True)
        return _deny("Voice session expired", 403, headers)

    if action == "close":
        lease_ref.set(
            {
                "active": False,
                "updated_at": _iso8601_z(now),
                "ended_at": _iso8601_z(now),
                "ended_reason": str(payload.get("reason") or "client_close"),
            },
            merge=True,
        )
        return (json.dumps({"ok": True, "closed": True}, ensure_ascii=False), 200, headers)

    lease_ref.set(
        {
            "updated_at": _iso8601_z(now),
            "last_heartbeat_at": _iso8601_z(now),
            "course_id": payload.get("course_id") or payload.get("courseId") or lease.get("course_id"),
            "presentation_id": payload.get("presentation_id") or payload.get("presentationId") or lease.get("presentation_id"),
            "slide_id": str(payload.get("slide_id") or payload.get("slideId") or lease.get("slide_id") or ""),
        },
        merge=True,
    )
    return (
        json.dumps(
            {
                "ok": True,
                "session_id": session_id,
                "expires_at": _iso8601_z(expires_at),
                "heartbeat_interval_seconds": int(lease.get("heartbeat_seconds") or heartbeat_seconds),
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
