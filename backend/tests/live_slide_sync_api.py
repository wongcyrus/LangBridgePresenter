#!/usr/bin/env python3
import argparse
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib import error, request


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _discover_tfstate(repo_root: Path) -> Path:
    patterns = [
        "backend/cdktf/terraform.cdktf-*.tfstate",
        "backend/cdktf/terraform.cdktf.tfstate",
    ]
    candidates = []
    for pattern in patterns:
        for raw in glob.glob(str(repo_root / pattern)):
            if raw.endswith(".backup"):
                continue
            candidates.append(Path(raw))
    if not candidates:
        raise FileNotFoundError("No cdktf tfstate file found under backend/cdktf/")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _extract_api_host(tfstate: Dict[str, Any]) -> str:
    outputs = tfstate.get("outputs", {})
    api_output = outputs.get("api-url", {})
    host = str(api_output.get("value", "")).strip()
    if not host:
        raise ValueError("Missing outputs['api-url'].value in tfstate")
    return host


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _extract_signing_keys(tfstate: Dict[str, Any]) -> Tuple[str, str]:
    default_secret = "default_secret_key"
    default_access = "default_access_key"
    found = []
    for node in _walk(tfstate):
        if "XIAOICE_CHAT_ACCESS_KEY" in node and "XIAOICE_CHAT_SECRET_KEY" in node:
            access_key = str(node["XIAOICE_CHAT_ACCESS_KEY"]).strip()
            secret_key = str(node["XIAOICE_CHAT_SECRET_KEY"]).strip()
            if access_key and secret_key:
                found.append((access_key, secret_key))
    if not found:
        raise ValueError("Could not find XIAOICE_CHAT_ACCESS_KEY / XIAOICE_CHAT_SECRET_KEY in tfstate")
    for access_key, secret_key in found:
        if access_key != default_access and secret_key != default_secret:
            return access_key, secret_key
    return found[0]


def _load_api_gateway_key(repo_root: Path) -> Optional[str]:
    env_value = os.getenv("API_GATEWAY_KEY", "").strip()
    if env_value:
        return env_value

    api_key_path = repo_root / "backend/admin_tools/api_key.json"
    if not api_key_path.exists():
        return None
    try:
        data = _load_json(api_key_path)
        return str(data.get("key_string") or data.get("api_key") or "").strip() or None
    except Exception:
        return None


def _sign_v2(body_string: str, secret_key: str, timestamp_ms: str) -> str:
    signature_string = "&".join(
        [
            f"bodyString={body_string}",
            f"secretKey={secret_key}",
            f"timestamp={timestamp_ms}",
        ]
    )
    return hashlib.sha512(signature_string.encode("utf-8")).hexdigest().upper()


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 20) -> Tuple[int, str]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test teacher live slide sync (/api/config) using values from cdktf tfstate."
    )
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--tfstate", default="", help="Optional tfstate path override")
    parser.add_argument("--api-key", default="", help="API Gateway key (fallback: API_GATEWAY_KEY env or backend/admin_tools/api_key.json)")
    parser.add_argument("--course-id", default="showcase")
    parser.add_argument("--ppt-filename", default="cloudtech.pptx")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=5)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    tfstate_path = Path(args.tfstate).resolve() if args.tfstate else _discover_tfstate(repo_root)
    tfstate = _load_json(tfstate_path)

    host = _extract_api_host(tfstate)
    api_url = f"https://{host}".rstrip("/")
    access_key, secret_key = _extract_signing_keys(tfstate)
    api_key = (args.api_key or _load_api_gateway_key(repo_root) or "").strip()
    if not api_key:
        print("ERROR: Missing API Gateway key. Pass --api-key or set API_GATEWAY_KEY.", file=sys.stderr)
        return 1

    endpoint = f"{api_url}/api/config?key={api_key}"

    print(f"Using tfstate: {tfstate_path}")
    print(f"API URL: {api_url}")
    print(f"Course: {args.course_id} | PPT: {args.ppt_filename}")
    print(f"Pages: {args.start_page}..{args.end_page}")
    print(f"Dry run: {args.dry_run}")
    print()

    step = 1 if args.end_page >= args.start_page else -1
    for page in range(args.start_page, args.end_page + step, step):
        payload = {
            "courseId": args.course_id,
            "ppt_filename": args.ppt_filename,
            "page_number": page,
            "context": f"live_sync_test_page_{page}",
        }
        body_string = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        timestamp = str(int(time.time() * 1000))
        signature = _sign_v2(body_string, secret_key, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Key": access_key,
            "X-Sign": signature,
        }

        print(f"Sync page {page} ... ", end="", flush=True)
        if args.dry_run:
            print("DRY RUN")
            continue

        status, text = _post_json(endpoint, payload, headers)
        if 200 <= status < 300:
            print(f"OK ({status})")
        else:
            print(f"FAILED ({status})")
            print(text)
            return 2
        time.sleep(max(0.0, args.sleep_seconds))

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
