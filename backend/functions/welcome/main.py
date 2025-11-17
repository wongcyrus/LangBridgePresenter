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
    
    config = get_config()
    welcome_messages = config.get("welcome_messages", {})
    
    reply = welcome_messages.get(
        language_code, welcome_messages.get("en", "Welcome!")
    )
    logger.debug("reply_text: %s", reply)
    response = {
        "id": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traceId": trace_id,
        "sessionId": session_id,
        "replyText": reply,
        "replyType": "Welcome",
        "timestamp": datetime.now().timestamp(),
        "extra": request_json.get("extra", {})
    }
    
    return json.dumps(response), 200, {"Content-Type": "application/json"}
