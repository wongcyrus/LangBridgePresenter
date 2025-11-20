"""Message generation logic with caching."""
import logging
import asyncio
from google.genai import types
from firestore_utils import (
    get_cached_presentation_message,
    cache_presentation_message
)
from agent_config import runner
from utils import normalize_context, session_id_for


logger = logging.getLogger(__name__)


def generate_presentation_message(language_code="en", context=""):
    """Generate a presentation message using the ADK agent with caching.
    
    Args:
        language_code: Target language (e.g., 'en', 'zh')
        context: Speaker notes from current slide
    """
    # Check cache first using speaker notes as key
    cached = get_cached_presentation_message(language_code, context)
    if cached:
        logger.info(
            "✅ Cache hit for %s (notes: %s...)",
            language_code, context[:30]
        )
        return cached
    
    logger.info("❌ Cache miss for %s, generating new message", language_code)
    
    # Generate new message from speaker notes
    if context:
        prompt = (
            f"Transform the following presentation speaker notes into a "
            f"clear, engaging message for students in {language_code} "
            f"language.\n\n"
            f"Speaker Notes:\n{context}\n\n"
            f"Generate a concise message (2-4 sentences) that captures the "
            f"key points. Return ONLY the message text, no explanations."
        )
    else:
        # Fallback if no speaker notes provided
        prompt = (
            f"Generate a warm, welcoming presentation introduction message "
            f"for a classroom presentation in {language_code}. "
            f"Keep it brief (1-2 sentences), professional, and engaging. "
            f"Return ONLY the message text, no explanations."
        )

    try:
        # Use per-notes session to avoid reusing earlier conversation
        session_id = session_id_for(language_code, context)
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
        
        # Cache the result only when context is non-empty after normalization
        if result:
            logger.info(
                "Generated text for %s, attempting cache write",
                language_code
            )
            if normalize_context(context):
                cache_presentation_message(language_code, result, context)
                logger.info("Cache write completed for %s", language_code)
            else:
                logger.info(
                    "Skipping cache write for %s due to empty context",
                    language_code,
                )
        else:
            logger.warning(
                "Generated empty result for %s, skipping cache",
                language_code
            )
        
        return result
    except Exception as e:
        logger.exception("Failed to generate presentation message: %s", e)
        # Don't cache failures
        return None
