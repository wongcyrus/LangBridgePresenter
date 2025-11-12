import json
import uuid
import functions_framework

@functions_framework.http
def recquestions(request):
    request_json = request.get_json(silent=True) or {}
    
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    
    recommended_questions = {
        "en": [
            "What can you help me with?",
            "How does this work?",
            "Can you explain more about this topic?"
        ],
        "zh": [
            "你能帮我做什么？",
            "这是如何工作的？",
            "你能详细解释一下这个话题吗？"
        ]
    }
    
    response = {
        "data": recommended_questions.get(language_code, recommended_questions["en"]),
        "traceId": trace_id
    }
    
    return json.dumps(response), 200, {"Content-Type": "application/json"}
