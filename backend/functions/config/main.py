import json
import logging
import os
import sys
import functions_framework
from google.cloud import firestore
from auth_utils import validate_authentication

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
def config(request):
    logger.debug("config invoked: method=%s", request.method)
    auth_error = validate_authentication(request)
    if auth_error:
        logger.warning("auth_error: %s", auth_error)
        return auth_error
    
    if request.method != 'POST':
        logger.warning("method not allowed: %s", request.method)
        return json.dumps({"error": "Method not allowed"}), 405, {
            "Content-Type": "application/json"
        }
    
    request_json = request.get_json(silent=True)
    if not request_json:
        logger.warning("invalid json body")
        return json.dumps({"error": "Invalid JSON"}), 400, {
            "Content-Type": "application/json"
        }
    
    try:
        db = firestore.Client(database="xiaoice")
        config_data = {
            "welcome_messages": request_json.get("welcome_messages", {}),
            "goodbye_messages": request_json.get("goodbye_messages", {}),
            "recommended_questions": request_json.get(
                "recommended_questions", {}
            ),
            "talk_responses": request_json.get("talk_responses", {}),
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('xiaoice_config').document('messages')
        doc_ref.set(config_data)
        logger.info("config updated in Firestore")
        return json.dumps({"success": True}), 200, {
            "Content-Type": "application/json"
        }
        
    except Exception as e:
        logger.exception("failed to update config: %s", e)
        return json.dumps({"error": str(e)}), 500, {
            "Content-Type": "application/json"
        }
