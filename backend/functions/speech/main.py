import json
import uuid
import logging
import os
import sys
import hashlib
from datetime import datetime
import functions_framework
from auth_utils import validate_authentication
from firestore_utils import get_config
from google.cloud import texttospeech, storage
import course_utils

_level_name = os.environ.get("LOG_LEVEL", "DEBUG").upper()
_level = getattr(logging, _level_name, logging.DEBUG)
_root = logging.getLogger()
_root.setLevel(_level)
if not any(isinstance(h, logging.StreamHandler) for h in _root.handlers):
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(asctime)s:%(message)s"
    )
    _handler.setFormatter(_formatter)
    _handler.setLevel(_level)
    _root.addHandler(_handler)
logger = logging.getLogger(__name__)
logger.setLevel(_level)


@functions_framework.http
def speech(request):
    logger.debug("speech invoked")
    auth_error = validate_authentication(request)
    if auth_error:
        logger.warning("auth_error: %s", auth_error)
        return auth_error

    request_json = request.get_json(silent=True) or {}
    logger.debug("request_json: %s", request_json)

    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    course_id = request_json.get("courseId")

    userParams = request_json.get("userParams", {})
    logger.debug("userParams: %s", userParams)

    is_presentation = False
    if isinstance(userParams, str):
        is_presentation = "presentation" in userParams.lower()

    config = get_config()

    if is_presentation:
        messages = config.get("presentation_messages", {})
        logger.debug("Using presentation_messages")
        reply = messages.get(language_code, messages.get("en", "Hello"))
    else:
        messages = config.get("welcome_messages", {})
        logger.debug("Using welcome_messages")
        reply = messages.get(language_code, messages.get("en", "Welcome!"))

    bucket_name = os.environ.get("SPEECH_FILE_BUCKET")
    if not bucket_name:
        logger.error("SPEECH_FILE_BUCKET env var missing")
        error_resp = {"error": "Server configuration error"}
        return (
            json.dumps(error_resp),
            500,
            {"Content-Type": "application/json"}
        )

    audio_url = None
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Generate stable filename from message content and language
        content_hash = hashlib.sha256(
            f"{reply}:{language_code}".encode("utf-8")
        ).hexdigest()[:12]
        filename = f"speech_{language_code}_{content_hash}.mp3"
        blob = bucket.blob(filename)
        
        # Check if file already exists
        if blob.exists():
            logger.info("Using cached speech file: %s", filename)
        else:
            logger.info("Generating new speech file: %s", filename)
            tts_client = texttospeech.TextToSpeechClient()
            
            # Use Course Config for Voice Selection
            voice = course_utils.get_voice_params(course_id, language_code)
            
            synthesis_input = texttospeech.SynthesisInput(text=reply)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0
            )
            tts_response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            blob.upload_from_string(
                tts_response.audio_content,
                content_type="audio/mpeg"
            )

        # Direct public URL (bucket is publicly readable)
        audio_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
    except Exception as e:
        logger.error("Text-to-Speech or upload failed: %s", e)
        error_resp = {"error": "Speech synthesis failed", "details": str(e)}
        return (
            json.dumps(error_resp),
            500,
            {"Content-Type": "application/json"}
        )

    response = {
        "id": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traceId": trace_id,
        "sessionId": session_id,
        "voiceUrl": audio_url,
        "replyType": "Voice",
        "timestamp": datetime.now().timestamp(),
        "extra": request_json.get("extra", {})
    }

    return json.dumps(response), 200, {"Content-Type": "application/json"}

