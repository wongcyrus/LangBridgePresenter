#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def _load_outputs(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid outputs file format: {path}")

    if "cdktf" in data and isinstance(data["cdktf"], dict):
        return data["cdktf"]

    for value in data.values():
        if isinstance(value, dict) and "project-id" in value:
            return value

    raise RuntimeError(f"Invalid outputs file format: {path}")


def _access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        check=True,
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Failed to get gcloud access token")
    return token


def _request_json(method: str, url: str, token: str, quota_project: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": quota_project,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _is_config_not_found(err: urllib.error.HTTPError) -> bool:
    try:
        body = err.read().decode("utf-8")
        payload = json.loads(body)
        return payload.get("error", {}).get("message") == "CONFIGURATION_NOT_FOUND"
    except Exception:
        return False


def ensure_identity_platform_initialized(client_project_id: str, token: str) -> None:
    config_url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{client_project_id}/config"
    try:
        _request_json("GET", config_url, token, client_project_id)
        print("Identity Platform config exists.")
        return
    except urllib.error.HTTPError as err:
        if err.code != 404 or not _is_config_not_found(err):
            raise

    init_url = (
        f"https://identitytoolkit.googleapis.com/admin/v2/projects/{client_project_id}"
        "/identityPlatform:initializeAuth"
    )
    _request_json("POST", init_url, token, client_project_id, {})
    _request_json("GET", config_url, token, client_project_id)
    print("Initialized Identity Platform auth config.")


def ensure_google_provider(
    client_project_id: str,
    firebase_api_key: str,
    oauth_client_id: str,
    oauth_client_secret: str,
    token: str,
) -> None:
    provider_url = (
        "https://identitytoolkit.googleapis.com/v2/projects/"
        f"{client_project_id}/defaultSupportedIdpConfigs/google.com"
    )
    payload = {
        "enabled": True,
        "clientId": oauth_client_id,
        "clientSecret": oauth_client_secret,
    }
    try:
        _request_json(
            "PATCH",
            provider_url + "?updateMask=enabled,clientId,clientSecret",
            token,
            client_project_id,
            payload,
        )
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        create_url = (
            "https://identitytoolkit.googleapis.com/v2/projects/"
            f"{client_project_id}/defaultSupportedIdpConfigs?idpId=google.com"
        )
        _request_json("POST", create_url, token, client_project_id, payload)

    verify_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:createAuthUri?key="
        + urllib.parse.quote(firebase_api_key)
    )
    verify_body = {
        "providerId": "google.com",
        "continueUri": f"https://{client_project_id}.firebaseapp.com/__/auth/handler",
    }
    req = urllib.request.Request(
        verify_url,
        data=json.dumps(verify_body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body) if body else {}
    auth_uri = payload.get("authUri", "")
    if not auth_uri:
        raise RuntimeError("Failed to verify Google sign-in provider configuration")
    print("Google sign-in provider configured and verified.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Firebase auth + Google provider for client project")
    parser.add_argument(
        "--outputs-file",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cdktf_outputs.json")),
        help="Path to cdktf outputs json (default: backend/cdktf_outputs.json)",
    )
    args = parser.parse_args()

    outputs = _load_outputs(args.outputs_file)
    client_project_id = outputs.get("client-project-id")
    firebase_api_key = outputs.get("firebase-api-key")
    if not client_project_id:
        raise RuntimeError("client-project-id missing from outputs")

    token = _access_token()
    ensure_identity_platform_initialized(client_project_id, token)

    oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    oauth_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if oauth_client_id and oauth_client_secret:
        if not firebase_api_key:
            raise RuntimeError("firebase-api-key missing from outputs; required to verify Google provider")
        ensure_google_provider(
            client_project_id=client_project_id,
            firebase_api_key=firebase_api_key,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=oauth_client_secret,
            token=token,
        )
    elif oauth_client_id or oauth_client_secret:
        raise RuntimeError("Both GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are required")
    else:
        print("Skipping Google provider setup (GOOGLE_OAUTH_CLIENT_ID/SECRET not provided).")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"bootstrap_client_auth failed: {exc}", file=sys.stderr)
        raise
