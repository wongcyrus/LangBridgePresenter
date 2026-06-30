import json
import logging
import os
import sys

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


@functions_framework.http
def voice_chat_access(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method != "GET":
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    try:
        decoded = _verify_user(request)
    except Exception as e:
        logger.warning("voice_chat_access auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    db = firestore.Client(database="langbridge")
    granted = _has_voice_access(decoded, db)
    payload = {
        "granted": granted,
        "uid": decoded.get("uid"),
        "email": decoded.get("email"),
    }
    if not granted:
        payload["reason"] = "Voice chat access requires admin grant"
    return (json.dumps(payload), 200, headers)
