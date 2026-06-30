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
        "requests_per_minute": int(os.environ.get("VOICE_CHAT_REQUESTS_PER_MINUTE", "10")),
        "requests_per_day": int(os.environ.get("VOICE_CHAT_REQUESTS_PER_DAY", "200")),
    }


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
        if "requests_per_minute" not in payload or "requests_per_day" not in payload:
            return (json.dumps({"error": "requests_per_minute and requests_per_day are required"}), 400, headers)
        try:
            per_min = int(payload["requests_per_minute"])
            per_day = int(payload["requests_per_day"])
        except (TypeError, ValueError):
            return (json.dumps({"error": "Limit values must be integers"}), 400, headers)
        if per_min <= 0 or per_day <= 0:
            return (json.dumps({"error": "Limit values must be > 0"}), 400, headers)
        if per_min > 1000 or per_day > 100000:
            return (json.dumps({"error": "Limit values are too high"}), 400, headers)

        settings_ref.set(
            {
                "requests_per_minute": per_min,
                "requests_per_day": per_day,
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
                        "requests_per_minute": per_min,
                        "requests_per_day": per_day,
                    },
                }
            ),
            200,
            headers,
        )

    settings_snap = settings_ref.get()
    if settings_snap.exists:
        limits = settings_snap.to_dict()
    else:
        limits = _default_limits()

    usage_docs = db.collection("voice_chat_usage").order_by(
        "day_count", direction=firestore.Query.DESCENDING
    ).limit(50).stream()

    usage = []
    total_today = 0
    today_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    for doc in usage_docs:
        data = doc.to_dict() or {}
        day_count = int(data.get("day_count", 0))
        if data.get("day_key") == today_key:
            total_today += day_count
        usage.append(
            {
                "uid": doc.id,
                "day_key": data.get("day_key"),
                "day_count": day_count,
                "minute_key": data.get("minute_key"),
                "minute_count": int(data.get("minute_count", 0)),
            }
        )

    return (
        json.dumps(
            {
                "limits": {
                    "requests_per_minute": int(limits.get("requests_per_minute", _default_limits()["requests_per_minute"])),
                    "requests_per_day": int(limits.get("requests_per_day", _default_limits()["requests_per_day"])),
                },
                "summary": {
                    "tracked_users": len(usage),
                    "total_today_requests": total_today,
                },
                "top_usage": usage,
            },
            ensure_ascii=False,
        ),
        200,
        headers,
    )
