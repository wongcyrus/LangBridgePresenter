import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

import firebase_admin
import functions_framework
from firebase_admin import auth as firebase_auth
from flask import Request, Response, stream_with_context
from google import genai
from google.cloud import firestore, storage, texttospeech


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


def _canonical_language_code(language_code: str) -> str:
    if not language_code:
        return "en-US"
    mapping = {
        "en": "en-US",
        "zh": "zh-CN",
        "yue": "yue-HK",
        "en-us": "en-US",
        "zh-cn": "zh-CN",
        "yue-hk": "yue-HK",
    }
    return mapping.get(language_code.lower(), language_code)


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


def _verify_firebase_user(request: Request):
    token = _extract_bearer_token(request)
    if not token:
        raise PermissionError("Missing bearer token")
    return firebase_auth.verify_id_token(token)


def _enforce_usage_limit(db: firestore.Client, uid: str):
    default_min = int(os.environ.get("VOICE_CHAT_REQUESTS_PER_MINUTE", "10"))
    default_day = int(os.environ.get("VOICE_CHAT_REQUESTS_PER_DAY", "200"))
    now = datetime.now(timezone.utc)
    minute_key = now.strftime("%Y%m%d%H%M")
    day_key = now.strftime("%Y%m%d")
    usage_ref = db.collection("voice_chat_usage").document(uid)
    settings_ref = db.collection("voice_chat_settings").document("default")

    @firestore.transactional
    def update_usage(transaction):
        settings_snap = settings_ref.get(transaction=transaction)
        settings = settings_snap.to_dict() if settings_snap.exists else {}
        per_min_limit = int(settings.get("requests_per_minute", default_min))
        per_day_limit = int(settings.get("requests_per_day", default_day))

        snap = usage_ref.get(transaction=transaction)
        usage = snap.to_dict() if snap.exists else {}
        current_minute_count = 0
        current_day_count = 0

        if usage.get("minute_key") == minute_key:
            current_minute_count = int(usage.get("minute_count", 0))
        if usage.get("day_key") == day_key:
            current_day_count = int(usage.get("day_count", 0))

        if current_minute_count >= per_min_limit:
            raise RuntimeError("minute_limit_exceeded")
        if current_day_count >= per_day_limit:
            raise RuntimeError("day_limit_exceeded")

        new_data = {
            "minute_key": minute_key,
            "minute_count": current_minute_count + 1,
            "day_key": day_key,
            "day_count": current_day_count + 1,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        transaction.set(usage_ref, new_data, merge=True)
        return {
            "minute_limit": per_min_limit,
            "minute_used": new_data["minute_count"],
            "day_limit": per_day_limit,
            "day_used": new_data["day_count"],
        }

    tx = db.transaction()
    return update_usage(tx)


def _fetch_slide_context(client_db: firestore.Client, course_id: str, presentation_id: str, slide_id: str):
    if not (course_id and presentation_id and slide_id):
        raise ValueError("courseId, presentationId and slideId are required")

    slide_ref = (
        client_db.collection("presentation_broadcast")
        .document(course_id)
        .collection("presentations")
        .document(presentation_id)
        .collection("slides")
        .document(str(slide_id))
    )
    snap = slide_ref.get()
    if not snap.exists:
        raise FileNotFoundError(
            f"Slide not found: presentation_broadcast/{course_id}/presentations/{presentation_id}/slides/{slide_id}"
        )
    return snap.to_dict()


def _build_prompt(question: str, language_code: str, slide_data: dict):
    lang = _canonical_language_code(language_code)
    languages = slide_data.get("languages", {})
    lang_data = languages.get(lang, {})
    slide_text = (lang_data.get("text") or "").strip()
    source_context = (slide_data.get("source_context") or "").strip()
    if not slide_text and not source_context:
        raise ValueError("No slide text available for the selected language.")

    return f"""
You are a classroom assistant for a presentation slide.
Answer in language: {lang}
Use only the provided slide data. If the answer is not in the data, reply exactly:
"Not mentioned in this slide."

Slide text ({lang}):
{slide_text or "(none)"}

Speaker notes:
{source_context or "(none)"}

Question:
{question}
""".strip()


def _generate_answer(prompt: str):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
    model = os.environ.get("VOICE_CHAT_GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(vertexai=True, project=project_id, location=location)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned empty answer")
    return answer


def _stream_answer(prompt: str):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
    model = os.environ.get("VOICE_CHAT_GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(vertexai=True, project=project_id, location=location)
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=prompt,
    ):
        text = getattr(chunk, "text", None) or ""
        if text:
            yield text


def _synthesize_answer_audio(answer: str, language_code: str, course_id: str):
    bucket_name = os.environ.get("SPEECH_FILE_BUCKET")
    if not bucket_name:
        raise RuntimeError("SPEECH_FILE_BUCKET env var missing")

    lang = _canonical_language_code(language_code)
    content_hash = hashlib.sha256(f"{answer}:{lang}".encode("utf-8")).hexdigest()[:12]
    filename = f"voicechat/{course_id}/speech_{lang}_{content_hash}.mp3"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    if not blob.exists():
        tts_client = texttospeech.TextToSpeechClient()
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
        )
        response = tts_client.synthesize_speech(
            request={
                "input": texttospeech.SynthesisInput(text=answer),
                "voice": voice,
                "audio_config": audio_config,
            }
        )
        blob.upload_from_string(response.audio_content, content_type="audio/mpeg")

    return f"https://storage.googleapis.com/{bucket_name}/{filename}"


@functions_framework.http
def voice_chat(request: Request):
    headers = _cors_headers()
    if request.method == "OPTIONS":
        return ("", 204, headers)
    if request.method != "POST":
        return (json.dumps({"error": "Method not allowed"}), 405, headers)

    try:
        decoded = _verify_firebase_user(request)
        uid = decoded.get("uid")
        if not uid:
            raise PermissionError("Invalid auth token")
    except Exception as e:
        logger.warning("Auth failed: %s", e)
        return (json.dumps({"error": "Unauthorized"}), 401, headers)

    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return (json.dumps({"error": "question is required"}), 400, headers)

    course_id = payload.get("courseId", "showcase")
    presentation_id = payload.get("presentationId")
    slide_id = payload.get("slideId")
    language_code = payload.get("languageCode", "en-US")
    stream_mode = bool(payload.get("stream"))

    try:
        db = firestore.Client(database="langbridge")
        usage = _enforce_usage_limit(db, uid)
    except RuntimeError as e:
        msg = str(e)
        if msg in {"minute_limit_exceeded", "day_limit_exceeded"}:
            return (json.dumps({"error": "Usage limit exceeded", "limit": msg}), 429, headers)
        logger.error("Usage tracking failed: %s", e)
        return (json.dumps({"error": "Usage validation failed"}), 500, headers)

    try:
        client_project_id = os.environ.get("CLIENT_FIRESTORE_PROJECT_ID")
        if not client_project_id:
            raise RuntimeError("CLIENT_FIRESTORE_PROJECT_ID env var missing")

        client_db = firestore.Client(
            project=client_project_id,
            database=os.environ.get("CLIENT_FIRESTORE_DATABASE_ID", "(default)"),
        )
        slide_data = _fetch_slide_context(client_db, course_id, presentation_id, slide_id)
        prompt = _build_prompt(question, language_code, slide_data)

        if stream_mode:
            headers["Content-Type"] = "text/event-stream"
            headers["Cache-Control"] = "no-cache"
            headers["Connection"] = "keep-alive"

            def sse_event(data: dict):
                return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            @stream_with_context
            def generate():
                try:
                    yield sse_event({"type": "started"})
                    answer_parts = []
                    for text_chunk in _stream_answer(prompt):
                        answer_parts.append(text_chunk)
                        yield sse_event({"type": "chunk", "text": text_chunk})

                    answer = "".join(answer_parts).strip()
                    if not answer:
                        raise RuntimeError("Gemini returned empty streamed answer")

                    audio_url = _synthesize_answer_audio(answer, language_code, course_id)
                    yield sse_event({
                        "type": "final",
                        "question": question,
                        "answer": answer,
                        "audioUrl": audio_url,
                        "courseId": course_id,
                        "presentationId": presentation_id,
                        "slideId": str(slide_id),
                        "languageCode": _canonical_language_code(language_code),
                        "usage": usage,
                        "uid": uid,
                    })
                except GeneratorExit:
                    logger.info("voice_chat stream closed by client")
                except Exception as e:
                    logger.exception("voice_chat streaming failed")
                    yield sse_event({"type": "error", "error": str(e)})

            return Response(generate(), status=200, headers=headers)

        answer = _generate_answer(prompt)
        audio_url = _synthesize_answer_audio(answer, language_code, course_id)
    except Exception as e:
        logger.exception("voice_chat failed")
        return (json.dumps({"error": str(e)}), 500, headers)

    response = {
        "question": question,
        "answer": answer,
        "audioUrl": audio_url,
        "courseId": course_id,
        "presentationId": presentation_id,
        "slideId": str(slide_id),
        "languageCode": _canonical_language_code(language_code),
        "usage": usage,
        "uid": uid,
    }
    return (json.dumps(response, ensure_ascii=False), 200, headers)
