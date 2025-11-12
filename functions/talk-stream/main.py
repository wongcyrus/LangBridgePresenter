import json
import uuid
from datetime import datetime
import functions_framework

@functions_framework.http
def talk_stream(request):
    request_json = request.get_json(silent=True) or {}
    
    ask_text = request_json.get("askText", "")
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    
    mock_response = {
        "askText": ask_text,
        "extra": request_json.get("extra", {}),
        "id": trace_id,
        "replyPayload": None,
        "replyText": f"Mock response to: {ask_text}",
        "replyType": "Llm",
        "sessionId": session_id,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "traceId": trace_id,
        "isFinal": True,
    }
    
    return f"data: {json.dumps(mock_response)}\n\n", 200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*"
    }
