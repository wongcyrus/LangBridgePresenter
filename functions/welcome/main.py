import json
import uuid
from datetime import datetime
import functions_framework

@functions_framework.http
def welcome(request):
    request_json = request.get_json(silent=True) or {}
    
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    
    welcome_messages = {
        "en": "Welcome! How can I help you today?",
        "zh": "欢迎！今天我能为您做些什么？"
    }
    
    response = {
        "id": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traceId": trace_id,
        "sessionId": session_id,
        "replyText": welcome_messages.get(language_code, welcome_messages["en"]),
        "replyType": "Welcome",
        "timestamp": datetime.now().timestamp(),
        "extra": request_json.get("extra", {})
    }
    
    return json.dumps(response), 200, {"Content-Type": "application/json"}
