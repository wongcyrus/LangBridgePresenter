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


def _minutes_limit(db: firestore.Client) -> int:
    default_minutes = int(os.environ.get("VOICE_LIVE_MINUTES_PER_DAY", "120"))
    settings_snap = db.collection("voice_chat_settings").document("default").get()
    if not settings_snap.exists:
        return default_minutes
    settings = settings_snap.to_dict() or {}
    configured = settings.get("minutes_per_day")
    if configured is None:
        configured = settings.get("requests_per_day")
    try:
        minutes = int(configured)
    except (TypeError, ValueError):
        minutes = default_minutes
    return max(1, minutes)


def _day_key(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y%m%d")


def _usage_daily_ref(db: firestore.Client, uid: str, day_key: str):
    return db.collection("voice_live_usage_daily").document(f"{uid}:{day_key}")


def _current_used_seconds(db: firestore.Client, uid: str, day_key: str) -> int:
    snap = _usage_daily_ref(db, uid, day_key).get()
    if not snap.exists:
        return 0
    data = snap.to_dict() or {}
    return max(0, int(data.get("used_seconds", 0)))


def _seconds_by_day(start_ts: datetime, end_ts: datetime) -> dict:
    if end_ts <= start_ts:
        return {}
    cursor = start_ts
    out = {}
    while cursor < end_ts:
        next_day = datetime(cursor.year, cursor.month, cursor.day, tzinfo=timezone.utc) + timedelta(days=1)
        segment_end = min(end_ts, next_day)
        seconds = int((segment_end - cursor).total_seconds())
        if seconds > 0:
            key = _day_key(cursor)
            out[key] = out.get(key, 0) + seconds
        cursor = segment_end
    return out


def _append_usage_log(db: firestore.Client, *, uid: str, email: str, lease: dict, ended_at: datetime, ended_reason: str):
    started_at_raw = lease.get("created_at")
    started_at = _parse_iso8601(started_at_raw) if started_at_raw else ended_at
    log_id = f"{uid}:{lease.get('session_id') or secrets.token_urlsafe(8)}"
    db.collection("voice_live_usage_logs").document(log_id).set(
        {
            "uid": uid,
            "email": (email or "").strip().lower(),
            "session_id": lease.get("session_id"),
            "course_id": lease.get("course_id"),
            "presentation_id": lease.get("presentation_id"),
            "slide_id": str(lease.get("slide_id") or ""),
            "started_at": _iso8601_z(started_at),
            "ended_at": _iso8601_z(ended_at),
            "duration_seconds": int(lease.get("accumulated_seconds") or 0),
            "day_key": _day_key(ended_at),
            "ended_reason": ended_reason,
            "updated_at": _iso8601_z(ended_at),
        },
        merge=True,
    )


def _deny(message: str, status_code: int, headers: dict):
    return (json.dumps({"error": message}, ensure_ascii=False), status_code, headers)


def _deny_with_payload(payload: dict, status_code: int, headers: dict):
    return (json.dumps(payload, ensure_ascii=False), status_code, headers)


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
    minutes_per_day = _minutes_limit(db)
    limit_seconds = minutes_per_day * 60
    today_key = _day_key(now)
    used_seconds_today = _current_used_seconds(db, uid, today_key)
    lease_ref = db.collection("voice_live_sessions").document(uid)
    lease_snap = lease_ref.get()
    lease = lease_snap.to_dict() if lease_snap.exists else {}

    if action == "open":
        if used_seconds_today >= limit_seconds:
            return _deny_with_payload(
                {
                    "error": "Daily voice minutes limit exceeded",
                    "code": "quota_exceeded",
                    "minutes_per_day": minutes_per_day,
                    "used_minutes_today": used_seconds_today // 60,
                },
                403,
                headers,
            )
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
                "accumulated_seconds": 0,
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
                    "minutes_per_day": minutes_per_day,
                    "used_minutes_today": used_seconds_today // 60,
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
        _append_usage_log(
            db,
            uid=uid,
            email=(decoded.get("email") or ""),
            lease=lease,
            ended_at=now,
            ended_reason="lease_expired",
        )
        return _deny("Voice session expired", 403, headers)

    last_heartbeat_raw = lease.get("last_heartbeat_at") or lease.get("created_at")
    try:
        last_heartbeat = _parse_iso8601(last_heartbeat_raw) if last_heartbeat_raw else now
    except Exception:
        last_heartbeat = now
    elapsed_by_day = _seconds_by_day(last_heartbeat, now)
    elapsed_total = sum(elapsed_by_day.values())
    if elapsed_total > 0:
        for usage_day_key, seconds in elapsed_by_day.items():
            usage_ref = _usage_daily_ref(db, uid, usage_day_key)
            usage_snap = usage_ref.get()
            current_seconds = int((usage_snap.to_dict() or {}).get("used_seconds", 0)) if usage_snap.exists else 0
            usage_ref.set(
                {
                    "uid": uid,
                    "email": (decoded.get("email") or "").strip().lower(),
                    "day_key": usage_day_key,
                    "used_seconds": max(0, current_seconds + seconds),
                    "updated_at": _iso8601_z(now),
                },
                merge=True,
            )

    used_seconds_today = _current_used_seconds(db, uid, today_key)
    next_accumulated_seconds = int(lease.get("accumulated_seconds") or 0) + max(0, elapsed_total)
    if used_seconds_today >= limit_seconds:
        ended_reason = "quota_exceeded"
        lease_ref.set(
            {
                "active": False,
                "updated_at": _iso8601_z(now),
                "ended_at": _iso8601_z(now),
                "ended_reason": ended_reason,
                "accumulated_seconds": next_accumulated_seconds,
            },
            merge=True,
        )
        _append_usage_log(
            db,
            uid=uid,
            email=(decoded.get("email") or ""),
            lease={**lease, "accumulated_seconds": next_accumulated_seconds},
            ended_at=now,
            ended_reason=ended_reason,
        )
        return _deny_with_payload(
            {
                "error": "Daily voice minutes limit exceeded",
                "code": "quota_exceeded",
                "minutes_per_day": minutes_per_day,
                "used_minutes_today": used_seconds_today // 60,
            },
            403,
            headers,
        )

    if action == "close":
        lease_ref.set(
            {
                "active": False,
                "updated_at": _iso8601_z(now),
                "ended_at": _iso8601_z(now),
                "ended_reason": str(payload.get("reason") or "client_close"),
                "accumulated_seconds": next_accumulated_seconds,
            },
            merge=True,
        )
        _append_usage_log(
            db,
            uid=uid,
            email=(decoded.get("email") or ""),
            lease={**lease, "accumulated_seconds": next_accumulated_seconds},
            ended_at=now,
            ended_reason=str(payload.get("reason") or "client_close"),
        )
        return (json.dumps({"ok": True, "closed": True}, ensure_ascii=False), 200, headers)

    lease_ref.set(
        {
            "updated_at": _iso8601_z(now),
            "last_heartbeat_at": _iso8601_z(now),
            "accumulated_seconds": next_accumulated_seconds,
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
                "minutes_per_day": minutes_per_day,
                "used_minutes_today": used_seconds_today // 60,
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
