import json
import uuid
from datetime import datetime
import functions_framework

@functions_framework.http
def goodbye(request):
    request_json = request.get_json(silent=True) or {}
    
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    
    goodbye_messages = {
        "en": "Goodbye! Have a great day!",
        "zh": "再见！祝您有美好的一天！"
    }
    
    response = {
        "id": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traceId": trace_id,
        "sessionId": session_id,
        "replyText": goodbye_messages.get(language_code, goodbye_messages["en"]),
        "replyType": "Goodbye",
        "timestamp": datetime.now().timestamp(),
        "extra": request_json.get("extra", {})
    }
    
    return json.dumps(response), 200, {"Content-Type": "application/json"}
