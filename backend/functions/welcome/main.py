import json
import uuid
import logging
import os
import sys
from datetime import datetime
import functions_framework
from auth_utils import validate_authentication
from firestore_utils import get_config

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

    userParams = request_json.get("userParams", {})
    logger.debug("userParams: %s", userParams)

    presenter_id = None
    if isinstance(userParams, dict):
        presenter_id = userParams.get("presenterId")
    elif isinstance(userParams, str):
        # Handle string format like "summer-presentation" or just "summer"
        if "-" in userParams:
            parts = userParams.split("-")
            # Heuristic: assume the first part is the ID if the second is 'presentation'
            # or just take the first part as a best guess.
            if len(parts) > 0:
                presenter_id = parts[0]
        else:
            presenter_id = userParams
            
    logger.debug(f"Extracted presenter_id: {presenter_id}")

    presenter = None
    if presenter_id:
        from firestore_utils import get_document
        presenter = get_document("presenters", presenter_id)
        logger.debug(f"Fetched presenter: {presenter}")
        if presenter and "language" in presenter:
            language_code = presenter["language"]
            logger.debug(f"Using presenter language: {language_code}")

    # Check if this is a presentation context
    is_presentation = False
    if isinstance(userParams, str):
        is_presentation = "presentation" in userParams.lower()
    
    config = get_config()
    
    # Use presentation_messages if presentation context,
    # otherwise welcome_messages
    if is_presentation:
        logger.debug("Using presentation_messages logic")
        
        # Map simple language codes to full codes used in the configuration
        LANG_CODE_MAP = {
            "en": "en-US",
            "zh": "zh-CN",
            "yue": "yue-HK",
            "yue-HK": "yue-HK",
            "zh-CN": "zh-CN",
            "en-US": "en-US"
        }
        target_lang = LANG_CODE_MAP.get(language_code, "en-US")
        logger.debug(f"Targeting language: {target_lang} for code: {language_code}")

        presentation_messages = config.get("presentation_messages", {})
        message_data = presentation_messages.get(target_lang)

        if message_data and isinstance(message_data, dict) and "text" in message_data:
            reply = message_data["text"]
        elif isinstance(message_data, str):
            reply = message_data
        else:
            # Fallback to English if target lang not found
            logger.warning(f"No presentation message found for {target_lang}, falling back to en-US")
            fallback_data = presentation_messages.get("en-US", {})
            if isinstance(fallback_data, dict):
                reply = fallback_data.get("text", "Hello")
            elif isinstance(fallback_data, str):
                reply = fallback_data
            else:
                reply = "Hello"
    else:
        messages = config.get("welcome_messages", {})        
        logger.debug("Using welcome_messages")    
        reply = messages.get(language_code, messages.get("en", "Welcome!"))
        
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
