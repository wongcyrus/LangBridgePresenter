import json
import logging
import os
import sys
import asyncio
import functions_framework
from google.cloud import firestore
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from firestore_utils import (
    get_cached_presentation_message,
    cache_presentation_message
)

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


# Initialize the ADK agent for generating messages
def create_agent():
    """Create and return an ADK agent for message generation."""
    return Agent(
        model="gemini-2.5-flash-lite",
        name='message_generator',
        description=(
            "A creative assistant that generates "
            "classroom messages and greetings."
        ),
        instruction=(
            "You are a creative assistant that generates warm, "
            "friendly, and appropriate messages for classroom settings. "
            "Generate messages that are welcoming, encouraging, "
            "and culturally sensitive."
        ),
    )


# Create runner (reusable across requests)
agent = create_agent()
runner = InMemoryRunner(
    agent=agent,
    app_name='xiaoice_message_generator',
)


def generate_presentation_message(language_code="en", context=""):
    """Generate a presentation message using the ADK agent with caching."""
    # Check cache first
    cached = get_cached_presentation_message(language_code, context)
    if cached:
        return cached
    
    # Generate new message
    prompt = (
        f"Generate a presentation introduction message "
        f"for a classroom presentation in {language_code}. "
    )
    if context:
        prompt += f"Context: {context}. "
    prompt += (
        "Keep it brief (1-2 sentences), professional, and engaging. "
        "Return ONLY the message text, no explanations."
    )

    try:
        session_id = f"presentation_gen_{language_code}"
        user_id = "system"

        # Get or create session
        session = asyncio.run(
            runner.session_service.get_session(
                app_name='xiaoice_message_generator',
                user_id=user_id,
                session_id=session_id,
            )
        )
        if session is None:
            session = asyncio.run(
                runner.session_service.create_session(
                    app_name='xiaoice_message_generator',
                    user_id=user_id,
                    session_id=session_id,
                )
            )

        content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=prompt)]
        )

        generated_text = ""
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if getattr(event, "content", None) and event.content.parts:
                part0 = event.content.parts[0]
                text = getattr(part0, "text", "") or ""
                if text:
                    generated_text += text

        result = generated_text.strip()
        
        # Cache the result
        if result:
            cache_presentation_message(language_code, result, context)
        
        return result
    except Exception as e:
        logger.exception("Failed to generate presentation message: %s", e)
        return None


@functions_framework.http
def config(request):
    logger.debug("config invoked: method=%s", request.method)

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

        # Handle presentation message generation if requested
        presentation_messages = request_json.get("presentation_messages", {})
        if request_json.get("generate_presentation", False):
            logger.info("Generating presentation messages with agent")
            languages = request_json.get("languages", ["en"])
            context = request_json.get("context", "")

            for lang in languages:
                generated = generate_presentation_message(lang, context)
                if generated:
                    presentation_messages[lang] = generated
                    logger.info(
                        "Generated presentation for %s: %s",
                        lang,
                        generated
                    )

        config_data = {
            "presentation_messages": presentation_messages,
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
