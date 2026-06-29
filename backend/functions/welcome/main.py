import json
import uuid
import logging
import os
import sys
from datetime import datetime
import functions_framework
from auth_utils import validate_authentication
from firestore_utils import get_config, get_document
from _shared.context_utils import (
    canonical_language_code,
    extract_presenter_ids,
    has_presentation_context,
    resolve_message_text,
)

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
def welcome(request):
    logger.debug("welcome invoked")
    auth_error = validate_authentication(request)
    if auth_error:
        logger.warning("auth_error: %s", auth_error)
        return auth_error
    
    request_json = request.get_json(silent=True) or {}
    logger.debug("request_json: %s", request_json)
    
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")

    user_params = request_json.get("userParams", {})
    logger.debug("userParams: %s", user_params)

    presenter_ids = extract_presenter_ids(user_params)
    presenter_id = presenter_ids[0] if presenter_ids else None
    logger.debug("Extracted presenter_ids: %s", presenter_ids)

    presenter = None
    if presenter_id:
        presenter = get_document("presenters", presenter_id)
        logger.debug("Fetched presenter: %s", presenter)
        if presenter and "language" in presenter:
            language_code = presenter["language"]
            logger.debug("Using presenter language: %s", language_code)

    # Check if this is a presentation context
    # Use presentation_messages if presentation context,
    # otherwise welcome_messages
    if has_presentation_context(user_params) and presenter:
        logger.debug("Using current_slide_languages from presenter")
        # Get current slide languages directly from presenter
        current_slide_languages = presenter.get("current_slide_languages", {})
        target_lang = canonical_language_code(language_code)
        logger.debug("Targeting language: %s for code: %s", target_lang, language_code)
        reply = resolve_message_text(
            current_slide_languages,
            [target_lang, "en-US", "en"],
            "Hello",
        )
        if reply == "Hello":
            logger.warning(
                "No presentation message found for %s, falling back to default",
                target_lang,
            )
    else:
        # Non-presentation context: use config
        config = get_config()
        messages = config.get("welcome_messages", {})        
        logger.debug("Using welcome_messages")    
        reply = resolve_message_text(
            messages,
            [canonical_language_code(language_code), language_code, "en"],
            "Welcome!",
        )
        
    logger.debug("reply_text: %s", reply)
    response = {
        "id": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traceId": trace_id,
        "sessionId": session_id,
        "replyText": reply,
        "replyType": "Llm",
        "timestamp": datetime.now().timestamp(),
        "extra": request_json.get("extra", {})
    }
    
    return json.dumps(response), 200, {"Content-Type": "application/json"}
