import json
import logging
import os
import secrets
import sys
import uuid
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import urlopen

import firebase_admin
import functions_framework
from firebase_admin import auth as firebase_auth
from flask import Request
from google.cloud import firestore, storage


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


def _normalize_email(raw_value: str) -> str:
    return (raw_value or "").strip().lower()


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


def _is_teacher(decoded_token: dict, db: firestore.Client) -> bool:
    uid = decoded_token.get("uid")
    email = _normalize_email(decoded_token.get("email") or "")
    if uid:
        teacher_snap = db.collection("teacher_users").document(uid).get()
        if teacher_snap.exists and (teacher_snap.to_dict() or {}).get("active") is True:
            return True
    if email:
        email_snap = db.collection("teacher_users").document(f"email:{email}").get()
        if email_snap.exists and (email_snap.to_dict() or {}).get("active") is True:
            if uid:
                uid_snap = db.collection("teacher_users").document(uid).get()
                uid_existing = uid_snap.to_dict() if uid_snap.exists else {}
                db.collection("teacher_users").document(uid).set(
                    {
                        "uid": uid,
                        "email": email,
                        "active": True,
                        "created_at": uid_existing.get("created_at", firestore.SERVER_TIMESTAMP),
                        "updated_at": firestore.SERVER_TIMESTAMP,
                        "updated_by": uid,
                    },
                    merge=True,
                )
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


def _normalize_languages(raw_languages):
    if isinstance(raw_languages, list):
        values = [str(v).strip() for v in raw_languages]
    elif isinstance(raw_languages, str):
        values = [v.strip() for v in raw_languages.split(",")]
    else:
        values = []
    normalized = [v for v in values if v]
    if not normalized:
        normalized = ["en-US", "zh-CN", "yue-HK"]
    return list(dict.fromkeys(normalized))


def _default_package_bucket():
    return (os.environ.get("COURSE_PACKAGE_BUCKET") or os.environ.get("SPEECH_FILE_BUCKET") or "").strip()


def _to_public_gcs_url(bucket_name: str, object_name: str):
    return f"https://storage.googleapis.com/{bucket_name}/{object_name}"


def _normalize_object_path(path_value: str):
    return str(path_value or "").strip().lstrip("/")


def _is_http_url(value: str):
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _manifest_content_hash(manifest: dict):
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _package_id_from_manifest(manifest: dict):
    candidate = str(manifest.get("package_id") or "").strip()
    if candidate:
        return candidate
    return f"pkg_{_manifest_content_hash(manifest)[:16]}"


def _resolve_manifest_object_path(prefix: str, raw_path: str):
    normalized = _normalize_object_path(raw_path)
    if not normalized:
        return ""
    if normalized.startswith("gs://"):
        trimmed = normalized[5:]
        return trimmed.split("/", 1)[1] if "/" in trimmed else ""
    clean_prefix = _normalize_object_path(prefix)
    if clean_prefix and not normalized.startswith(clean_prefix):
        return f"{clean_prefix}/{normalized}"
    return normalized


def _load_package_manifest_from_url(*, manifest_url: str):
    if not _is_http_url(manifest_url):
        raise ValueError("Invalid manifest_url: must be http(s)")
    try:
        with urlopen(manifest_url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to load manifest_url: {e}") from e
    if not isinstance(payload, dict):
        raise ValueError("Invalid package manifest: root must be an object")
    presentations = payload.get("presentations")
    if not isinstance(presentations, list) or not presentations:
        raise ValueError("Invalid package manifest: presentations must be a non-empty list")
    return payload


def _validate_package_manifest(*, bucket_name: str, package_prefix: str, manifest: dict):
    missing = []
    slides_total = 0
    languages_total = 0
    for presentation in manifest.get("presentations", []):
        presentation_id = str(presentation.get("presentation_id") or "").strip()
        slides = presentation.get("slides")
        if not presentation_id:
            raise ValueError("Invalid package manifest: presentation_id is required")
        if not isinstance(slides, list) or not slides:
            raise ValueError(f"Invalid package manifest: slides required for presentation {presentation_id}")
        for slide in slides:
            slide_id = str(slide.get("slide_id") or "").strip()
            lang_map = slide.get("languages")
            if not slide_id:
                raise ValueError(f"Invalid package manifest: slide_id required in presentation {presentation_id}")
            if not isinstance(lang_map, dict) or not lang_map:
                raise ValueError(f"Invalid package manifest: languages required for slide {presentation_id}/{slide_id}")
            slides_total += 1
            for _lang_code, lang_entry in lang_map.items():
                if not isinstance(lang_entry, dict):
                    raise ValueError(f"Invalid package manifest: language entry must be object for {presentation_id}/{slide_id}")
                text_value = str(lang_entry.get("text") or "").strip()
                if not text_value:
                    raise ValueError(f"Invalid package manifest: text required for {presentation_id}/{slide_id}")
                languages_total += 1
                for url_field in ("audio_url", "image_url"):
                    raw_url = str(lang_entry.get(url_field) or "").strip()
                    if raw_url and not _is_http_url(raw_url):
                        raise ValueError(
                            f"Invalid package manifest: {url_field} must be http(s) URL for {presentation_id}/{slide_id}"
                        )
                for legacy_field in ("audio_path", "image_path"):
                    if str(lang_entry.get(legacy_field) or "").strip():
                        raise ValueError(
                            f"Invalid package manifest: {legacy_field} is not supported; use audio_url/image_url for {presentation_id}/{slide_id}"
                        )
    if missing:
        first = missing[0]
        raise ValueError(
            "Package validation failed: missing object "
            f"{first['path']} ({first['field']} at {first['presentation_id']}/{first['slide_id']})"
        )
    return {"presentations": len(manifest.get("presentations", [])), "slides": slides_total, "languages": languages_total}


def _build_class_broadcast_from_manifest(*, db: firestore.Client, class_id: str, bucket_name: str, package_prefix: str, manifest: dict):
    root_ref = db.collection("presentation_broadcast").document(class_id)
    presentations = manifest.get("presentations", [])
    first_presentation = presentations[0]
    first_slide = first_presentation.get("slides", [])[0]
    current_presentation_id = str(manifest.get("current_presentation_id") or first_presentation.get("presentation_id") or "")
    current_slide_id = str(manifest.get("current_slide_id") or first_slide.get("slide_id") or "")
    root_ref.set(
        {
            "current_presentation_id": current_presentation_id,
            "current_slide_id": current_slide_id,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "package_bucket": bucket_name,
            "package_prefix": package_prefix,
        },
        merge=False,
    )
    for presentation in presentations:
        presentation_id = str(presentation.get("presentation_id") or "").strip()
        if not presentation_id:
            continue
        ppt_ref = root_ref.collection("presentations").document(presentation_id)
        ppt_ref.set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=False)
        for slide in presentation.get("slides", []):
            slide_id = str(slide.get("slide_id") or "").strip()
            if not slide_id:
                continue
            languages_payload = {}
            for lang_code, lang_entry in (slide.get("languages") or {}).items():
                if not isinstance(lang_entry, dict):
                    continue
                lang_obj = {"text": str(lang_entry.get("text") or "")}
                audio_url = str(lang_entry.get("audio_url") or "").strip()
                image_url = str(lang_entry.get("image_url") or "").strip()
                if audio_url:
                    lang_obj["audio_url"] = audio_url
                if image_url:
                    lang_obj["slide_link"] = image_url
                languages_payload[lang_code] = lang_obj
            ppt_ref.collection("slides").document(slide_id).set(
                {
                    "languages": languages_payload,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                    "course_id": class_id,
                    "presentation_id": presentation_id,
                    "slide_id": slide_id,
                },
                merge=False,
            )
    return {"current_presentation_id": current_presentation_id, "current_slide_id": current_slide_id}


def _course_from_doc(doc):
    data = doc.to_dict() or {}
    return {
        "course_id": data.get("course_id") or doc.id,
        "title": data.get("title"),
        "description": data.get("description"),
        "languages": data.get("languages") or [],
        "voice_configs": data.get("voice_configs") or {},
        "teacher_uid": data.get("teacher_uid"),
        "teacher_email": data.get("teacher_email"),
        "package_bucket": data.get("package_bucket"),
        "package_prefix": data.get("package_prefix"),
        "package_manifest_path": data.get("package_manifest_path"),
        "package_manifest_url": data.get("package_manifest_url"),
        "package_version": data.get("package_version"),
        "package_id": data.get("package_id"),
        "package_status": data.get("package_status"),
        "active": data.get("active") is not False,
        "created_at": _to_iso8601(data.get("created_at")),
        "updated_at": _to_iso8601(data.get("updated_at")),
    }


def _class_from_doc(doc):
    data = doc.to_dict() or {}
    return {
        "class_id": data.get("class_id") or doc.id,
        "title": data.get("title"),
        "course_id": data.get("course_id"),
        "source_presentation_course_id": data.get("source_presentation_course_id"),
        "teacher_uid": data.get("teacher_uid"),
        "teacher_email": data.get("teacher_email"),
        "is_public": data.get("is_public") is True,
        "package_id": data.get("package_id"),
        "package_manifest_path": data.get("package_manifest_path"),
        "package_manifest_url": data.get("package_manifest_url"),
        "package_version": data.get("package_version"),
        "active": data.get("active") is not False,
        "current_presentation_id": data.get("current_presentation_id"),
        "current_slide_id": data.get("current_slide_id"),
        "created_at": _to_iso8601(data.get("created_at")),
        "updated_at": _to_iso8601(data.get("updated_at")),
    }


def _list_courses(db: firestore.Client, *, uid: str, is_admin: bool):
    courses = []
    query = db.collection("courses")
    if not is_admin:
        query = query.where("teacher_uid", "==", uid)
    for doc in query.stream():
        courses.append(_course_from_doc(doc))
    courses.sort(key=lambda row: (row.get("updated_at") or "", row.get("title") or ""), reverse=True)
    return courses[:300]


def _list_classes(db: firestore.Client, *, uid: str, is_admin: bool):
    classes = []
    query = db.collection("classes")
    if not is_admin:
        query = query.where("teacher_uid", "==", uid)
    for doc in query.stream():
        classes.append(_class_from_doc(doc))
    classes.sort(key=lambda row: (row.get("updated_at") or "", row.get("title") or ""), reverse=True)
    return classes[:300]


def _clone_presentation_broadcast(db: firestore.Client, *, source_course_id: str, target_class_id: str):
    src_root = db.collection("presentation_broadcast").document(source_course_id)
    src_snap = src_root.get()
    if not src_snap.exists:
        raise ValueError(f"Source presentation_broadcast not found: {source_course_id}")

    src_data = src_snap.to_dict() or {}
    dst_root = db.collection("presentation_broadcast").document(target_class_id)
    dst_root.set(
        {
            **src_data,
            "source_course_id": source_course_id,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=False,
    )

    for src_ppt_doc in src_root.collection("presentations").stream():
        src_ppt_data = src_ppt_doc.to_dict() or {}
        dst_ppt_ref = dst_root.collection("presentations").document(src_ppt_doc.id)
        dst_ppt_ref.set(src_ppt_data, merge=False)

        for src_slide_doc in src_root.collection("presentations").document(src_ppt_doc.id).collection("slides").stream():
            dst_ppt_ref.collection("slides").document(src_slide_doc.id).set(src_slide_doc.to_dict() or {}, merge=False)


def _set_student_status(db: firestore.Client, *, class_id: str, uid: str, email: str, status: str, updated_by: str):
    now = firestore.SERVER_TIMESTAMP
    class_student_ref = db.collection("classes").document(class_id).collection("students").document(uid)
    class_student_ref.set(
        {
            "uid": uid,
            "email": _normalize_email(email),
            "status": status,
            "active": status not in {"inactive", "removed"},
            "updated_at": now,
            "updated_by": updated_by,
        },
        merge=True,
    )

    enrollment_ref = db.collection("student_enrollments").document(uid).collection("classes").document(class_id)
    enrollment_ref.set(
        {
            "class_id": class_id,
            "status": status,
            "active": status not in {"inactive", "removed"},
            "updated_at": now,
            "updated_by": updated_by,
        },
        merge=True,
    )


def _set_student_status_by_email(db: firestore.Client, *, class_id: str, email: str, status: str, updated_by: str):
    now = firestore.SERVER_TIMESTAMP
    normalized_email = _normalize_email(email)
    principal_id = f"email:{normalized_email}"
    class_student_ref = db.collection("classes").document(class_id).collection("students").document(principal_id)
    class_student_ref.set(
        {
            "principal_id": principal_id,
            "uid": None,
            "email": normalized_email,
            "status": status,
            "active": status not in {"inactive", "removed"},
            "updated_at": now,
            "updated_by": updated_by,
        },
        merge=True,
    )
    enrollment_ref = db.collection("student_enrollments").document(principal_id).collection("classes").document(class_id)
    enrollment_ref.set(
        {
            "class_id": class_id,
            "principal_id": principal_id,
            "uid": None,
            "email": normalized_email,
            "status": status,
            "active": status not in {"inactive", "removed"},
            "updated_at": now,
            "updated_by": updated_by,
        },
        merge=True,
    )


@functions_framework.http
def teacher_courses(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method not in {"GET", "POST"}:
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    db = firestore.Client(database="langbridge")
    try:
        decoded = _verify_user(request)
    except Exception as e:
        logger.warning("teacher_courses auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    uid = decoded.get("uid")
    email = _normalize_email(decoded.get("email") or "")
    if not uid:
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    admin = _is_admin(decoded, db)
    teacher = _is_teacher(decoded, db)
    if not admin and not teacher:
        return (json.dumps({"error": "Forbidden"}), 403, headers)

    if request.method == "GET":
        payload = {
            "is_admin": admin,
            "is_teacher": teacher or admin,
            "courses": _list_courses(db, uid=uid, is_admin=admin),
            "classes": _list_classes(db, uid=uid, is_admin=admin),
        }
        return (json.dumps(payload, ensure_ascii=False), 200, headers)

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "").strip().lower()

    if action == "create_course":
        title = str(payload.get("title") or "").strip()
        if not title:
            return (json.dumps({"error": "title is required"}), 400, headers)
        course_id = str(payload.get("course_id") or "").strip() or f"course_{secrets.token_hex(6)}"
        description = str(payload.get("description") or "").strip()
        languages = _normalize_languages(payload.get("languages"))
        voice_configs = payload.get("voice_configs") or {}

        db.collection("courses").document(course_id).set(
            {
                "course_id": course_id,
                "title": title,
                "description": description,
                "languages": languages,
                "voice_configs": voice_configs,
                "teacher_uid": uid,
                "teacher_email": email,
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=False,
        )
        return (json.dumps({"ok": True, "course_id": course_id}, ensure_ascii=False), 200, headers)

    if action == "update_course":
        course_id = str(payload.get("course_id") or "").strip()
        if not course_id:
            return (json.dumps({"error": "course_id is required"}), 400, headers)
        course_ref = db.collection("courses").document(course_id)
        course_snap = course_ref.get()
        if not course_snap.exists:
            return (json.dumps({"error": "Course not found"}), 404, headers)
        course_data = course_snap.to_dict() or {}
        if not admin and course_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        updates = {"updated_at": firestore.SERVER_TIMESTAMP}
        if "title" in payload:
            updates["title"] = str(payload.get("title") or "").strip()
        if "description" in payload:
            updates["description"] = str(payload.get("description") or "").strip()
        if "languages" in payload:
            updates["languages"] = _normalize_languages(payload.get("languages"))
        if "voice_configs" in payload and isinstance(payload.get("voice_configs"), dict):
            updates["voice_configs"] = payload.get("voice_configs")
        if "active" in payload:
            updates["active"] = bool(payload.get("active"))
        course_ref.set(updates, merge=True)
        return (json.dumps({"ok": True, "course_id": course_id}, ensure_ascii=False), 200, headers)

    if action == "create_upload_session":
        course_id = str(payload.get("course_id") or "").strip()
        if not course_id:
            return (json.dumps({"error": "course_id is required"}), 400, headers)
        course_ref = db.collection("courses").document(course_id)
        course_snap = course_ref.get()
        if not course_snap.exists:
            return (json.dumps({"error": "Course not found"}), 404, headers)
        course_data = course_snap.to_dict() or {}
        if not admin and course_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        bucket_name = str(payload.get("package_bucket") or _default_package_bucket()).strip()
        package_prefix = _normalize_object_path(str(payload.get("package_prefix") or f"course-packages/{course_id}"))
        file_paths = payload.get("file_paths") or []
        if isinstance(file_paths, str):
            file_paths = [line.strip() for line in file_paths.splitlines() if line.strip()]
        if not bucket_name:
            return (json.dumps({"error": "package_bucket is required"}), 400, headers)
        if not isinstance(file_paths, list) or not file_paths:
            return (json.dumps({"error": "file_paths is required"}), 400, headers)

        upload_id = secrets.token_hex(8)
        upload_prefix = f"{package_prefix}/incoming/{upload_id}"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        upload_urls = []
        for raw_path in file_paths:
            relative_path = _normalize_object_path(str(raw_path))
            if not relative_path:
                continue
            object_name = f"{upload_prefix}/{relative_path}"
            blob = bucket.blob(object_name)
            try:
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=3600,
                    method="PUT",
                    content_type="application/octet-stream",
                )
            except Exception as e:
                return (json.dumps({"error": f"Failed to generate signed URL for {relative_path}: {e}"}), 500, headers)
            upload_urls.append({"path": relative_path, "object_name": object_name, "upload_url": signed_url})
        return (
            json.dumps(
                {
                    "ok": True,
                    "course_id": course_id,
                    "package_bucket": bucket_name,
                    "upload_prefix": upload_prefix,
                    "upload_urls": upload_urls,
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    if action == "link_course_package":
        course_id = str(payload.get("course_id") or "").strip()
        if not course_id:
            return (json.dumps({"error": "course_id is required"}), 400, headers)
        course_ref = db.collection("courses").document(course_id)
        course_snap = course_ref.get()
        if not course_snap.exists:
            return (json.dumps({"error": "Course not found"}), 404, headers)
        course_data = course_snap.to_dict() or {}
        if not admin and course_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        bucket_name = str(payload.get("package_bucket") or _default_package_bucket()).strip()
        package_prefix = _normalize_object_path(str(payload.get("package_prefix") or f"course-packages/{course_id}"))
        manifest_url_input = str(payload.get("manifest_url") or "").strip()
        if not _is_http_url(manifest_url_input):
            return (json.dumps({"error": "manifest_url is required and must be http(s) URL"}), 400, headers)
        manifest_url = manifest_url_input
        manifest = _load_package_manifest_from_url(manifest_url=manifest_url)
        validation = _validate_package_manifest(bucket_name=bucket_name, package_prefix=package_prefix, manifest=manifest)
        package_id = _package_id_from_manifest(manifest)
        package_hash = _manifest_content_hash(manifest)
        package_version = str(payload.get("package_version") or "").strip() or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M%S")
        db.collection("course_packages").document(package_id).set(
            {
                "package_id": package_id,
                "course_id": course_id,
                "package_bucket": bucket_name,
                "package_prefix": package_prefix,
                "manifest_path": "",
                "manifest_url": manifest_url,
                "package_version": package_version,
                "status": "ready",
                "content_hash": package_hash,
                "created_by": uid,
                "updated_by": uid,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        course_ref.set(
            {
                "package_id": package_id,
                "package_bucket": bucket_name,
                "package_prefix": package_prefix,
                "package_manifest_path": "",
                "package_manifest_url": manifest_url,
                "package_version": package_version,
                "package_status": "ready",
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        return (
            json.dumps(
                {
                    "ok": True,
                    "course_id": course_id,
                    "package_id": package_id,
                    "package_bucket": bucket_name,
                    "package_prefix": package_prefix,
                    "manifest_path": "",
                    "manifest_url": manifest_url,
                    "package_version": package_version,
                    "validation": validation,
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    if action == "clone_class_from_package":
        course_id = str(payload.get("course_id") or "").strip()
        if not course_id:
            return (json.dumps({"error": "course_id is required"}), 400, headers)
        course_ref = db.collection("courses").document(course_id)
        course_snap = course_ref.get()
        if not course_snap.exists:
            return (json.dumps({"error": "Course not found"}), 404, headers)
        course_data = course_snap.to_dict() or {}
        if not admin and course_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        bucket_name = str(course_data.get("package_bucket") or "").strip()
        package_prefix = _normalize_object_path(str(course_data.get("package_prefix") or ""))
        manifest_url = str(course_data.get("package_manifest_url") or "").strip()
        if not manifest_url:
            return (json.dumps({"error": "Course package is not linked"}), 400, headers)
        if not _is_http_url(manifest_url):
            return (json.dumps({"error": "Course package manifest_url is invalid"}), 400, headers)
        manifest = _load_package_manifest_from_url(manifest_url=manifest_url)
        _validate_package_manifest(bucket_name=bucket_name, package_prefix=package_prefix, manifest=manifest)

        class_title = str(payload.get("class_title") or "").strip() or f"{course_data.get('title') or course_id} Class"
        class_id = str(payload.get("class_id") or "").strip() or f"class_{secrets.token_hex(6)}"
        is_public = bool(payload.get("is_public"))
        pointers = _build_class_broadcast_from_manifest(
            db=db,
            class_id=class_id,
            bucket_name=bucket_name,
            package_prefix=package_prefix,
            manifest=manifest,
        )
        db.collection("classes").document(class_id).set(
            {
                "class_id": class_id,
                "title": class_title,
                "course_id": course_id,
                "teacher_uid": uid,
                "teacher_email": email,
                "is_public": is_public,
                "source_presentation_course_id": course_id,
                "current_presentation_id": pointers.get("current_presentation_id"),
                "current_slide_id": pointers.get("current_slide_id"),
                "package_id": course_data.get("package_id"),
                "package_bucket": bucket_name,
                "package_prefix": package_prefix,
                "package_manifest_path": "",
                "package_manifest_url": manifest_url,
                "package_version": course_data.get("package_version"),
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=False,
        )
        return (json.dumps({"ok": True, "class_id": class_id}, ensure_ascii=False), 200, headers)

    if action == "clone_class":
        course_id = str(payload.get("course_id") or "").strip()
        if not course_id:
            return (json.dumps({"error": "course_id is required"}), 400, headers)
        course_snap = db.collection("courses").document(course_id).get()
        if not course_snap.exists:
            return (json.dumps({"error": "Course not found"}), 404, headers)
        course_data = course_snap.to_dict() or {}
        if not admin and course_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        class_title = str(payload.get("class_title") or "").strip() or f"{course_data.get('title') or course_id} Class"
        class_id = str(payload.get("class_id") or "").strip() or f"class_{secrets.token_hex(6)}"
        is_public = bool(payload.get("is_public"))
        source_presentation_course_id = str(payload.get("source_presentation_course_id") or "").strip() or course_id
        try:
            _clone_presentation_broadcast(
                db,
                source_course_id=source_presentation_course_id,
                target_class_id=class_id,
            )
        except ValueError as e:
            return (json.dumps({"error": str(e)}), 400, headers)

        root_broadcast = db.collection("presentation_broadcast").document(class_id).get().to_dict() or {}
        db.collection("classes").document(class_id).set(
            {
                "class_id": class_id,
                "title": class_title,
                "course_id": course_id,
                "teacher_uid": uid,
                "teacher_email": email,
                "is_public": is_public,
                "source_presentation_course_id": source_presentation_course_id,
                "current_presentation_id": root_broadcast.get("current_presentation_id"),
                "current_slide_id": root_broadcast.get("current_slide_id"),
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=False,
        )
        return (json.dumps({"ok": True, "class_id": class_id}, ensure_ascii=False), 200, headers)

    if action == "set_student_status":
        class_id = str(payload.get("class_id") or "").strip()
        status = str(payload.get("status") or "").strip().lower() or "active"
        if not class_id:
            return (json.dumps({"error": "class_id is required"}), 400, headers)
        class_snap = db.collection("classes").document(class_id).get()
        if not class_snap.exists:
            return (json.dumps({"error": "Class not found"}), 404, headers)
        class_data = class_snap.to_dict() or {}
        if not admin and class_data.get("teacher_uid") != uid:
            return (json.dumps({"error": "Forbidden"}), 403, headers)

        student_uid = str(payload.get("student_uid") or "").strip()
        student_email = _normalize_email(str(payload.get("student_email") or ""))
        if not student_uid:
            if not student_email:
                return (json.dumps({"error": "student_uid or student_email is required"}), 400, headers)
            try:
                student_uid = firebase_auth.get_user_by_email(student_email).uid
            except Exception:
                student_uid = ""
        if not student_email:
            try:
                student_email = _normalize_email(firebase_auth.get_user(student_uid).email or "")
            except Exception:
                student_email = ""

        if student_uid:
            _set_student_status(
                db,
                class_id=class_id,
                uid=student_uid,
                email=student_email,
                status=status,
                updated_by=uid,
            )
        elif student_email:
            _set_student_status_by_email(
                db,
                class_id=class_id,
                email=student_email,
                status=status,
                updated_by=uid,
            )
        else:
            return (json.dumps({"error": "Unable to resolve student identity"}), 400, headers)
        return (
            json.dumps(
                {
                    "ok": True,
                    "class_id": class_id,
                    "student_uid": student_uid or None,
                    "student_email": student_email,
                    "status": status,
                },
                ensure_ascii=False,
            ),
            200,
            headers,
        )

    return (json.dumps({"error": f"Unsupported action: {action}"}), 400, headers)
