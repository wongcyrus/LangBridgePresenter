import json
import uuid
import logging
import os
import sys
from datetime import datetime
import functions_framework
from auth_utils import validate_authentication
from firestore_utils import get_config
from google.adk.agents.llm_agent import Agent


# Robust logging setup that works on Cloud Functions/Cloud Run
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


# Initialize the ADK agent with Gemini 2.5 Flash
def create_agent():
    """Create and return an ADK agent for conversation."""
    return Agent(
        model='gemini-2.5-flash',
        name='classroom_assistant',
        description=(
            "A helpful classroom assistant "
            "that answers student questions."
        ),
        instruction=(
            "You are Xiaoice, a friendly and helpful classroom assistant. "
            "Respond to student questions in a clear, educational, and "
            "encouraging manner. "
            "Keep responses concise but informative."
        ),
    )


@functions_framework.http
def talk_stream(request):
    logger.debug("talk_stream invoked")
    auth_error = validate_authentication(request)
    if auth_error:
        logger.warning("auth_error: %s", auth_error)
        return auth_error
    
    request_json = request.get_json(silent=True) or {}
    logger.debug("request_json: %s", request_json)
    
    ask_text = request_json.get("askText", "")
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    
    # Use ADK agent to generate response
    try:
        agent = create_agent()
        logger.debug("agent created: %s", type(agent).__name__)
        
        # Prepare the prompt with language context
        prompt = ask_text
        if language_code != "en":
            prompt = f"Please respond in {language_code}: {ask_text}"
        
        # Get response from the agent using send() method
        agent_response = agent.send(prompt)
        # Debug log of the raw agent response per request
        logger.debug("agent_response: %r", agent_response)
        response_text = (
            agent_response.text
            if hasattr(agent_response, 'text')
            else str(agent_response)
        )
        logger.debug("response_text: %s", response_text)
        
    except Exception:
        # Fallback to config-based response on error
        config = get_config()
        talk_responses = config.get("talk_responses", {})
        default_response = f"Mock response to: {ask_text}"
        response_text = talk_responses.get(
            language_code, talk_responses.get("en", default_response)
        )
        logger.exception("Error generating agent response; using fallback")
    
    mock_response = {
        "askText": ask_text,
        "extra": request_json.get("extra", {}),
        "id": trace_id,
        "replyPayload": None,
        "replyText": response_text,
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
