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

    # Check if this is a presentation context
    is_presentation = False
    if isinstance(userParams, str):
        is_presentation = "presentation" in userParams.lower()
    
    config = get_config()
    
    # Use presentation_messages if presentation context,
    # otherwise welcome_messages
    if is_presentation:
        messages = config.get("presentation_messages", {})       
        logger.debug("Using presentation_messages")
        reply = messages.get(
            language_code, messages.get("en", "Hello")
        )
    else:
        messages = config.get("welcome_messages", {})        
        logger.debug("Using welcome_messages")    
        reply = messages.get(
            language_code, messages.get("en", "Welcome!")
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
