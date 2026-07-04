import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
import functions_framework
from firebase_admin import auth as firebase_auth
from flask import Request
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

_DEFAULT_TTS_PROFILE = {
    "gender": "FEMALE",
    "speaking_rate": 1.0,
    "pitch": 0.0,
}
_AVATAR_TTS_PROFILE_MAP = {
    "chitose": {
        "gender": "MALE",
        "speaking_rate": 1.0,
        "pitch": -1.0,
    },
    "wild": {
        "gender": "MALE",
        "speaking_rate": 0.92,
        "pitch": -2.0,
    },
}


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


def _verify_firebase_user(request: Request):
    token = _extract_bearer_token(request)
    if not token:
        raise PermissionError("Missing bearer token")
    return firebase_auth.verify_id_token(token)


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


def _resolve_tts_profile(avatar_name: str) -> Dict[str, Any]:
    key = str(avatar_name or "").strip().lower()
    profile = _AVATAR_TTS_PROFILE_MAP.get(key)
    if not profile:
        return dict(_DEFAULT_TTS_PROFILE)
    merged = dict(_DEFAULT_TTS_PROFILE)
    merged.update(profile)
    return merged


def _has_text_chat_access(decoded_token: dict, db: firestore.Client) -> bool:
    uid = decoded_token.get("uid")
    email = (decoded_token.get("email") or "").strip().lower()
    if uid:
        snap = db.collection("text_chat_users").document(f"uid:{uid}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    if email:
        snap = db.collection("text_chat_users").document(f"email:{email}").get()
        if snap.exists and (snap.to_dict() or {}).get("active") is True:
            return True
    return False


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


def _normalize_chat_history(raw_history: Any, *, max_turns: int = 12, max_chars: int = 300) -> List[Dict[str, str]]:
    if not isinstance(raw_history, list):
        return []
    turns: List[Dict[str, str]] = []
    for item in raw_history[-max_turns:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars].rstrip()
        turns.append({"role": role, "text": text})
    return turns


def _build_prompt(
    question: str,
    language_code: str,
    slide_data: dict,
    chat_history: Optional[List[Dict[str, str]]] = None,
):
    lang = _canonical_language_code(language_code)
    languages = slide_data.get("languages", {})
    lang_data = languages.get(lang, {})
    slide_text = (lang_data.get("text") or "").strip()
    source_context = (slide_data.get("source_context") or "").strip()
    if not slide_text and not source_context:
        raise ValueError("No slide text available for the selected language.")
    history_lines = []
    for turn in (chat_history or []):
        role_label = "User" if turn.get("role") == "user" else "Tutor"
        history_lines.append(f"{role_label}: {turn.get('text', '')}")
    history_block = "\n".join(history_lines).strip() or "(none)"
    return f"""
You are a classroom tutor assistant.
Answer in language: {lang}
Default to treating the question as related to the current slide topic/content.
Treat references like "this slide", "this topic", "related news", "search information", "latest news", "recent example", or "real-world case" as related when they refer to the slide topic.
Only if the question is clearly unrelated to the slide topic, reply only with:
"I can only help with this slide. Please ask a question about the current slide content."
If the question is related to this slide, always use Google Search grounding before answering.
Use grounded external facts/examples to clarify the slide context, including latest developments when relevant.
Do not answer related questions using slide text alone; include grounded context in every related answer.
Keep grounded additions tightly tied to the slide topic, and do not switch to unrelated topics.
Use recent conversation history for follow-up context.
Give concise answer suitable for students.
Do not repeat points, examples, or sentences.
Maximum 6 sentences total.

Slide text ({lang}):
{slide_text or "(none)"}

Speaker notes:
{source_context or "(none)"}

Recent conversation (oldest to newest):
{history_block}

Question:
{question}
""".strip()


def _dedupe_answer_text(answer: str) -> str:
    text = str(answer or "").strip()
    if not text:
        return text

    parts = [p.strip() for p in text.splitlines() if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in text.replace("\n", " ").split("。") if p.strip()]
        if parts:
            parts = [f"{p}。" for p in parts]
    seen = set()
    cleaned = []
    for part in parts:
        key = " ".join(part.split()).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(part.strip())

    merged = "\n".join(cleaned).strip()
    if len(merged) > 1800:
        merged = merged[:1800].rstrip()
    return merged


def _weekly_key(now_utc: datetime) -> str:
    iso_year, iso_week, _iso_weekday = now_utc.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _default_budget_settings() -> Dict[str, Any]:
    return {
        "weekly_budget_usd": float(os.environ.get("TEXT_CHAT_WEEKLY_BUDGET_USD", "5")),
        "price_input_per_million": float(os.environ.get("TEXT_CHAT_PRICE_INPUT_PER_MILLION", "0.25")),
        "price_output_per_million": float(os.environ.get("TEXT_CHAT_PRICE_OUTPUT_PER_MILLION", "1.5")),
        "grounding_price_per_query": float(os.environ.get("TEXT_CHAT_GROUNDING_PRICE_PER_QUERY", "0.014")),
        "projected_output_tokens": int(os.environ.get("TEXT_CHAT_PROJECTED_OUTPUT_TOKENS", "1200")),
        "projected_grounding_queries": int(os.environ.get("TEXT_CHAT_PROJECTED_GROUNDING_QUERIES", "1")),
    }


def _load_budget_settings(db: firestore.Client) -> Dict[str, Any]:
    defaults = _default_budget_settings()
    snap = db.collection("text_chat_budget_settings").document("default").get()
    if not snap.exists:
        return defaults
    raw = snap.to_dict() or {}
    def _num_float(key: str) -> float:
        try:
            return float(raw.get(key, defaults[key]))
        except (TypeError, ValueError):
            return float(defaults[key])
    def _num_int(key: str) -> int:
        try:
            return int(raw.get(key, defaults[key]))
        except (TypeError, ValueError):
            return int(defaults[key])
    return {
        "weekly_budget_usd": _num_float("weekly_budget_usd"),
        "price_input_per_million": _num_float("price_input_per_million"),
        "price_output_per_million": _num_float("price_output_per_million"),
        "grounding_price_per_query": _num_float("grounding_price_per_query"),
        "projected_output_tokens": _num_int("projected_output_tokens"),
        "projected_grounding_queries": _num_int("projected_grounding_queries"),
    }


def _cost_usd(*, input_tokens: int, output_tokens: int, grounding_queries: int, settings: Dict[str, Any]) -> float:
    input_cost = (max(0, int(input_tokens)) / 1_000_000.0) * float(settings["price_input_per_million"])
    output_cost = (max(0, int(output_tokens)) / 1_000_000.0) * float(settings["price_output_per_million"])
    grounding_cost = max(0, int(grounding_queries)) * float(settings["grounding_price_per_query"])
    return float(input_cost + output_cost + grounding_cost)


def _read_usage_value(usage: Any, key: str) -> Optional[int]:
    value = None
    if usage is not None:
        if isinstance(usage, dict):
            value = usage.get(key)
        else:
            value = getattr(usage, key, None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_grounding_queries(response: Any, default_queries: int) -> int:
    try:
        data = response.to_dict()
    except Exception:
        data = {}

    keys = {
        "web_search_queries",
        "google_search_queries",
        "search_queries",
        "grounding_queries",
    }

    def _walk(node: Any) -> Optional[int]:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in keys:
                    try:
                        return int(v)
                    except (TypeError, ValueError):
                        continue
                found = _walk(v)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found is not None:
                    return found
        return None

    extracted = _walk(data)
    if extracted is not None:
        return max(0, extracted)
    return max(0, int(default_queries))


def _extract_usage(response: Any, default_grounding_queries: int) -> Dict[str, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        usage = getattr(response, "usage", None)

    input_tokens = (
        _read_usage_value(usage, "prompt_token_count")
        or _read_usage_value(usage, "total_input_tokens")
        or _read_usage_value(usage, "input_tokens")
    )
    output_tokens = (
        _read_usage_value(usage, "candidates_token_count")
        or _read_usage_value(usage, "total_output_tokens")
        or _read_usage_value(usage, "output_tokens")
    )
    total_tokens = (
        _read_usage_value(usage, "total_token_count")
        or _read_usage_value(usage, "total_tokens")
    )
    tool_use_tokens = (
        _read_usage_value(usage, "total_tool_use_tokens")
        or _read_usage_value(usage, "tool_use_token_count")
        or 0
    )

    if input_tokens is None or output_tokens is None:
        raise RuntimeError("Missing token usage metadata from Gemini response")

    if total_tokens is None:
        total_tokens = input_tokens + output_tokens

    grounding_queries = _extract_grounding_queries(response, default_grounding_queries)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "tool_use_tokens": int(tool_use_tokens),
        "grounding_queries": grounding_queries,
    }


def _count_prompt_tokens(client: genai.Client, model: str, prompt: str) -> int:
    result = client.models.count_tokens(model=model, contents=prompt)
    count = getattr(result, "total_tokens", None)
    if count is None:
        count = result.get("total_tokens") if isinstance(result, dict) else None
    if count is None:
        raise RuntimeError("Gemini token counting did not return total_tokens")
    return int(count)


def _estimate_prompt_tokens(prompt: str) -> int:
    text = str(prompt or "")
    if not text:
        return 1
    # Fast server-side estimate to avoid an extra upstream API call before each tutor request.
    return max(1, min(32768, len(text) // 4))


def _check_budget_before_call(db: firestore.Client, uid: str, settings: Dict[str, Any], projected_input_tokens: int):
    now = datetime.now(timezone.utc)
    week_key = _weekly_key(now)
    spend_ref = db.collection("text_chat_spend").document(uid)
    spend_snap = spend_ref.get()
    current = spend_snap.to_dict() if spend_snap.exists else {}
    if current.get("week_key") == week_key:
        try:
            current_week_spent = float(current.get("spent_usd", 0))
        except (TypeError, ValueError):
            current_week_spent = 0.0
    else:
        current_week_spent = 0.0

    projected_cost = _cost_usd(
        input_tokens=projected_input_tokens,
        output_tokens=int(settings["projected_output_tokens"]),
        grounding_queries=int(settings["projected_grounding_queries"]),
        settings=settings,
    )
    projected_total = current_week_spent + projected_cost
    if projected_total > float(settings["weekly_budget_usd"]):
        raise PermissionError(
            f"Weekly budget exceeded: projected ${projected_total:.4f} > ${float(settings['weekly_budget_usd']):.2f}"
        )
    return {
        "week_key": week_key,
        "current_spent_usd": current_week_spent,
        "projected_cost_usd": projected_cost,
        "projected_total_usd": projected_total,
    }


def _commit_spend_after_call(
    db: firestore.Client,
    uid: str,
    settings: Dict[str, Any],
    usage: Dict[str, int],
):
    now = datetime.now(timezone.utc)
    week_key = _weekly_key(now)
    spend_ref = db.collection("text_chat_spend").document(uid)
    call_cost = _cost_usd(
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        grounding_queries=usage["grounding_queries"],
        settings=settings,
    )

    @firestore.transactional
    def _txn(transaction):
        snap = spend_ref.get(transaction=transaction)
        current = snap.to_dict() if snap.exists else {}
        if current.get("week_key") != week_key:
            current_spent = 0.0
            input_tokens = 0
            output_tokens = 0
            tool_use_tokens = 0
            total_tokens = 0
            grounding_queries = 0
            request_count = 0
        else:
            try:
                current_spent = float(current.get("spent_usd", 0))
            except (TypeError, ValueError):
                current_spent = 0.0
            try:
                input_tokens = int(current.get("input_tokens", 0))
            except (TypeError, ValueError):
                input_tokens = 0
            try:
                output_tokens = int(current.get("output_tokens", 0))
            except (TypeError, ValueError):
                output_tokens = 0
            try:
                tool_use_tokens = int(current.get("tool_use_tokens", 0))
            except (TypeError, ValueError):
                tool_use_tokens = 0
            try:
                total_tokens = int(current.get("total_tokens", 0))
            except (TypeError, ValueError):
                total_tokens = 0
            try:
                grounding_queries = int(current.get("grounding_queries", 0))
            except (TypeError, ValueError):
                grounding_queries = 0
            try:
                request_count = int(current.get("request_count", 0))
            except (TypeError, ValueError):
                request_count = 0

        next_spent = current_spent + call_cost
        payload = {
            "week_key": week_key,
            "spent_usd": next_spent,
            "input_tokens": input_tokens + usage["input_tokens"],
            "output_tokens": output_tokens + usage["output_tokens"],
            "tool_use_tokens": tool_use_tokens + usage["tool_use_tokens"],
            "total_tokens": total_tokens + usage["total_tokens"],
            "grounding_queries": grounding_queries + usage["grounding_queries"],
            "request_count": request_count + 1,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        transaction.set(spend_ref, payload, merge=True)
        return payload

    tx = db.transaction()
    totals = _txn(tx)
    budget = float(settings["weekly_budget_usd"])
    remaining = budget - float(totals["spent_usd"])
    return {
        "call_cost_usd": call_cost,
        "weekly_spent_usd": float(totals["spent_usd"]),
        "weekly_remaining_usd": remaining,
        "weekly_budget_usd": budget,
        "week_key": week_key,
    }


def _synthesize_answer_audio(answer: str, language_code: str, course_id: str, avatar_name: str):
    bucket_name = os.environ.get("SPEECH_FILE_BUCKET")
    if not bucket_name:
        raise RuntimeError("SPEECH_FILE_BUCKET env var missing")

    lang = _canonical_language_code(language_code)
    profile = _resolve_tts_profile(avatar_name)
    profile_key = str(profile.get("gender") or "FEMALE").upper()
    content_hash = hashlib.sha256(f"{answer}:{lang}:{profile_key}".encode("utf-8")).hexdigest()[:12]
    filename = f"textchat/{course_id}/speech_{lang}_{profile_key.lower()}_{content_hash}.mp3"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    if not blob.exists():
        tts_client = texttospeech.TextToSpeechClient()
        gender_name = str(profile.get("gender") or "FEMALE").upper()
        gender = getattr(texttospeech.SsmlVoiceGender, gender_name, texttospeech.SsmlVoiceGender.FEMALE)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang,
            ssml_gender=gender,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=float(profile.get("speaking_rate", 1.0)),
            pitch=float(profile.get("pitch", 0.0)),
        )
        tts_response = tts_client.synthesize_speech(
            request={
                "input": texttospeech.SynthesisInput(text=answer),
                "voice": voice,
                "audio_config": audio_config,
            }
        )
        blob.upload_from_string(tts_response.audio_content, content_type="audio/mpeg")

    return f"https://storage.googleapis.com/{bucket_name}/{filename}"


def _generate_answer(client: genai.Client, model: str, prompt: str):
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"tools": [{"google_search": {}}]},
    )
    answer = (getattr(response, "text", None) or "").strip()
    if not answer:
        raise RuntimeError("Gemini returned empty answer")
    return response, answer


def _extract_citations(response: Any, *, max_items: int = 6) -> List[str]:
    try:
        data = response.to_dict()
    except Exception:
        data = {}
    urls: List[str] = []
    seen = set()

    def _add_url(value: Any):
        if not isinstance(value, str):
            return
        raw = value.strip()
        if not raw:
            return
        if not raw.startswith(("http://", "https://")):
            return
        if raw in seen:
            return
        seen.add(raw)
        urls.append(raw)

    def _walk(node: Any):
        if len(urls) >= max_items:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("url", "uri", "source_uri", "retrieved_uri", "link"):
                    _add_url(value)
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)
        elif isinstance(node, str):
            for match in re.findall(r"https?://[^\s\]\)\"'<>]+", node):
                _add_url(match)

    _walk(data)
    return urls[:max_items]


@functions_framework.http
def tutor_ask(request: Request):
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
    if len(question) > 500:
        return (json.dumps({"error": "question is too long (max 500 chars)"}), 400, headers)

    course_id = str(payload.get("courseId") or "").strip()
    presentation_id = str(payload.get("presentationId") or "").strip()
    slide_id = str(payload.get("slideId") or "").strip()
    language_code = str(payload.get("languageCode") or "en-US").strip()
    avatar_name = str(payload.get("avatarName") or "").strip()
    if not course_id or not presentation_id or not slide_id:
        return (json.dumps({"error": "courseId, presentationId, and slideId are required"}), 400, headers)
    chat_history = _normalize_chat_history(payload.get("chatHistory"))

    db = firestore.Client(database="langbridge")
    if not _has_text_chat_access(decoded, db):
        return (json.dumps({"error": "Text chat access requires admin grant"}), 403, headers)

    settings = _load_budget_settings(db)
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    model = os.environ.get("TEXT_CHAT_GEMINI_MODEL", "gemini-2.5-flash-lite")
    client = genai.Client(vertexai=True, project=project_id, location=location)

    try:
        client_project_id = os.environ.get("CLIENT_FIRESTORE_PROJECT_ID")
        if not client_project_id:
            raise RuntimeError("CLIENT_FIRESTORE_PROJECT_ID env var missing")

        client_db = firestore.Client(
            project=client_project_id,
            database=os.environ.get("CLIENT_FIRESTORE_DATABASE_ID", "(default)"),
        )
        slide_data = _fetch_slide_context(client_db, course_id, presentation_id, slide_id)
        prompt = _build_prompt(question, language_code, slide_data, chat_history)

        projected_input_tokens = _estimate_prompt_tokens(prompt)
        projected = _check_budget_before_call(db, uid, settings, projected_input_tokens)

        response, answer = _generate_answer(client, model, prompt)
        answer = _dedupe_answer_text(answer)
        usage = _extract_usage(response, int(settings["projected_grounding_queries"]))
        citations = _extract_citations(response)
        spend = _commit_spend_after_call(db, uid, settings, usage)

        if spend["weekly_remaining_usd"] < 0:
            return (
                json.dumps(
                    {
                        "error": "Weekly text chat budget exceeded",
                        "spend": spend,
                    },
                    ensure_ascii=False,
                ),
                429,
                headers,
            )

        audio_url = _synthesize_answer_audio(answer, language_code, course_id, avatar_name)
    except PermissionError as e:
        return (json.dumps({"error": str(e)}), 429, headers)
    except Exception as e:
        logger.exception("tutor_ask failed")
        return (json.dumps({"error": str(e)}), 500, headers)

    response_payload = {
        "question": question,
        "answer": answer,
        "audioUrl": audio_url,
        "courseId": course_id,
        "presentationId": presentation_id,
        "slideId": slide_id,
        "languageCode": _canonical_language_code(language_code),
        "citations": citations,
        "usage": usage,
        "spend": spend,
        "projected": projected,
    }
    return (json.dumps(response_payload, ensure_ascii=False), 200, headers)
