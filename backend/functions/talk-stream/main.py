import json
import uuid
import logging
import os
import sys
from datetime import datetime
import asyncio
import functions_framework
from flask import Response
from auth_utils import validate_authentication
from firestore_utils import get_config
from google.adk.agents import config_agent_utils
from google.adk.runners import InMemoryRunner
from google.genai import types


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


# Initialize the ADK agent from YAML configuration
def create_agent():
    """Create and return an ADK agent from YAML config."""
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(
        current_dir, "talking_agent", "root_agent.yaml"
    )
    
    # Load the agent from the config file using utility function
    return config_agent_utils.from_config(config_file_path)


# Create runner (reusable across requests)
agent = create_agent()
runner = InMemoryRunner(
    agent=agent,
    app_name='langbridge_classroom_assistant',
)


@functions_framework.http
def talk_stream(request):
    """Streaming SSE response that mirrors the reference pattern.
    Yields incremental chunks followed by a final summary chunk.
    """
    logger.debug("talk_stream invoked")
    auth_error = validate_authentication(request)
    if auth_error:
        logger.warning("auth_error: %s", auth_error)
        return auth_error

    request_json = request.get_json(silent=True) or {}
    logger.debug("request_json: %s", request_json)

    ask_text = request_json.get("askText", "")
    # Use a stable conversation id (provided by client) and a stable user_id
    session_id = request_json.get("sessionId", str(uuid.uuid4()))
    user_id = request_json.get("userId", session_id)
    trace_id = request_json.get("traceId", str(uuid.uuid4()))
    language_code = request_json.get("languageCode", "en")
    extra = request_json.get("extra", {})

    def sse_format(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def stream_response():
        # Prepare the prompt with language context
        prompt = ask_text
        if language_code and language_code != "en":
            prompt = f"Please respond in {language_code}: {ask_text}"

        try:
            # Reuse an existing session if present; otherwise create one
            # with the given session_id
            session = asyncio.run(
                runner.session_service.get_session(
                    app_name='langbridge_classroom_assistant',
                    user_id=user_id,
                    session_id=session_id,
                )
            )
            if session is None:
                session = asyncio.run(
                    runner.session_service.create_session(
                        app_name='langbridge_classroom_assistant',
                        user_id=user_id,
                        session_id=session_id,
                    )
                )
                logger.debug(
                    "Session created: %s",
                    getattr(session, 'id', None),
                )
            else:
                logger.debug(
                    "Session reused: %s",
                    getattr(session, 'id', None),
                )

            content = types.Content(
                role='user',
                parts=[types.Part.from_text(text=prompt)]
            )

            accumulated_text = ""
            for event in runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                try:
                    text = ""
                    if getattr(event, "content", None) and event.content.parts:
                        part0 = event.content.parts[0]
                        text = getattr(part0, "text", "") or ""
                    if not text:
                        continue
                    accumulated_text += text
                    chunk = {
                        "askText": ask_text,
                        "extra": extra,
                        "id": trace_id,
                        "replyPayload": None,
                        "replyText": text,  # incremental piece
                        "replyType": "Llm",
                        "sessionId": session_id,
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "traceId": trace_id,
                        "isFinal": False,
                    }
                    logger.debug("Streaming chunk (%s chars)", len(text))
                    yield sse_format(chunk)
                except Exception:
                    logger.exception("Error while streaming a chunk")
            # Final chunk
            final_chunk = {
                "askText": ask_text,
                "extra": extra,
                "id": trace_id,
                "replyPayload": None,
                "replyText": accumulated_text,
                "replyType": "Llm",
                "sessionId": session_id,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "traceId": trace_id,
                "isFinal": True,
            }
            logger.debug("Final chunk length: %s", len(accumulated_text))
            yield sse_format(final_chunk)
        except Exception:
            logger.exception("Error generating agent response; using fallback")
            # Fallback to config-based response on error
            config = get_config()
            talk_responses = config.get("talk_responses", {})
            default_response = f"Mock response to: {ask_text}"
            response_text = talk_responses.get(
                language_code, talk_responses.get("en", default_response)
            )
            err_chunk = {
                "askText": ask_text,
                "extra": extra,
                "id": trace_id,
                "replyPayload": None,
                "replyText": response_text,
                "replyType": "Llm",
                "sessionId": session_id,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "traceId": trace_id,
                "isFinal": True,
            }
            yield sse_format(err_chunk)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "X-Accel-Buffering": "no",
    }
    return Response(
        stream_response(),
        mimetype="text/event-stream",
        headers=headers,
    )
