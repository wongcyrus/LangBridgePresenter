#!/usr/bin/env python3
import asyncio
import contextlib
import json
import logging
import os
from datetime import datetime, timezone

import certifi
import firebase_admin
import google.auth
import websockets
from firebase_admin import auth as firebase_auth
from google.auth.transport.requests import Request
from google.cloud import firestore
from websockets.exceptions import ConnectionClosed


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("voice-live-proxy")

PORT = int(os.environ.get("PORT", "8080"))
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
MODEL_ID = os.environ.get("VOICE_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
MAX_AUTH_WAIT_SECONDS = int(os.environ.get("VOICE_PROXY_AUTH_TIMEOUT_SECONDS", "10"))

_project_id = os.environ.get("CLIENT_FIREBASE_PROJECT_ID") or os.environ.get("CLIENT_FIRESTORE_PROJECT_ID")
if not firebase_admin._apps:
    if _project_id:
        firebase_admin.initialize_app(options={"projectId": _project_id})
    else:
        firebase_admin.initialize_app()


def _extract_firestore_database() -> str:
    return os.environ.get("FIRESTORE_DATABASE", "langbridge")


def _parse_iso8601(ts: str) -> datetime:
    normalized = (ts or "").replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _generate_access_token() -> str:
    creds, _ = google.auth.default()
    if not creds.valid:
        creds.refresh(Request())
    return creds.token


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


def _validate_live_lease(db: firestore.Client, uid: str, lease_session_id: str):
    lease_ref = db.collection("voice_live_sessions").document(uid)
    lease_snap = lease_ref.get()
    lease = lease_snap.to_dict() if lease_snap.exists else {}
    if not lease or lease.get("active") is not True:
        raise PermissionError("No active voice live lease")
    if not lease_session_id or lease_session_id != str(lease.get("session_id") or ""):
        raise PermissionError("Invalid voice live lease")
    expires_at = lease.get("expires_at")
    if not expires_at:
        raise PermissionError("Voice live lease expired")
    if datetime.now(timezone.utc) >= _parse_iso8601(expires_at):
        raise PermissionError("Voice live lease expired")
    return lease


def _gemini_live_service_url(project_id: str) -> str:
    model_uri = f"projects/{project_id}/locations/{GCP_LOCATION}/publishers/google/models/{MODEL_ID}"
    # Client will send setup message containing model as well; this URL is the bidi transport endpoint.
    _ = model_uri
    return "wss://us-central1-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"


async def _proxy_task(source, destination, direction: str):
    try:
        async for message in source:
            if direction == "upstream_to_client":
                try:
                    payload = json.loads(message)
                    if payload.get("setupComplete"):
                        logger.info("Upstream setupComplete received")
                    elif payload.get("error"):
                        logger.warning("Upstream error payload: %s", payload.get("error"))
                    elif payload.get("toolCall"):
                        calls = payload.get("toolCall", {}).get("functionCalls") or []
                        logger.info("Upstream toolCall received (%s calls)", len(calls))
                    elif payload.get("serverContent"):
                        server_content = payload.get("serverContent") or {}
                        if server_content.get("turnComplete"):
                            logger.info("Upstream turnComplete received")
                        model_turn = server_content.get("modelTurn") or {}
                        parts = model_turn.get("parts") or []
                        if parts:
                            logger.info("Upstream modelTurn parts received (%s parts)", len(parts))
                except Exception:
                    pass
            await destination.send(message)
    except ConnectionClosed as closed:
        logger.info(
            "Proxy stream closed (%s): code=%s reason=%s",
            direction,
            getattr(closed, "code", "unknown"),
            getattr(closed, "reason", ""),
        )
    finally:
        try:
            await destination.close()
        except Exception:
            pass


async def _handle_client(client_ws):
    try:
        raw_first = await asyncio.wait_for(client_ws.recv(), timeout=MAX_AUTH_WAIT_SECONDS)
        first_message = json.loads(raw_first)
    except asyncio.TimeoutError:
        await client_ws.close(code=4001, reason="Auth timeout")
        return
    except Exception:
        await client_ws.close(code=4002, reason="Invalid auth payload")
        return

    if first_message.get("type") != "auth":
        await client_ws.close(code=4003, reason="Missing auth message")
        return

    id_token = str(first_message.get("id_token") or "").strip()
    lease_session_id = str(first_message.get("lease_session_id") or "").strip()
    if not id_token or not lease_session_id:
        await client_ws.close(code=4004, reason="Missing id_token or lease_session_id")
        return

    try:
        decoded = firebase_auth.verify_id_token(id_token)
        uid = decoded.get("uid")
        if not uid:
            raise PermissionError("Unauthorized")
        db = firestore.Client(database=_extract_firestore_database())
        if not _has_voice_access(decoded, db):
            raise PermissionError("Voice chat access requires admin grant")
        _validate_live_lease(db, uid, lease_session_id)
    except Exception as error:
        logger.warning("Proxy auth rejected: %s", error)
        await client_ws.close(code=4005, reason="Unauthorized")
        return

    try:
        access_token = _generate_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        import ssl

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        service_url = _gemini_live_service_url(os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
        async with websockets.connect(service_url, extra_headers=headers, ssl=ssl_context) as upstream_ws:
            await client_ws.send(json.dumps({"type": "proxy_ready"}))
            client_to_upstream = asyncio.create_task(_proxy_task(client_ws, upstream_ws, "client_to_upstream"))
            upstream_to_client = asyncio.create_task(_proxy_task(upstream_ws, client_ws, "upstream_to_client"))
            done, pending = await asyncio.wait(
                [client_to_upstream, upstream_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            for task in done:
                _ = task.result() if not task.cancelled() else None
    except Exception as error:
        logger.exception("Upstream proxy failure")
        if not client_ws.closed:
            await client_ws.close(code=1011, reason=f"Upstream error: {error}")


async def _main():
    logger.info("Starting voice-live proxy on port %s", PORT)
    async with websockets.serve(_handle_client, "0.0.0.0", PORT, max_size=8 * 1024 * 1024):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Proxy stopped")
