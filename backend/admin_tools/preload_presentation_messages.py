#!/usr/bin/env python3
"""
Pre-generate presentation_messages from PPTX speaker notes and cache them
for fast retrieval by generate_presentation_message().

This tool:
1. Reads speaker notes from each slide
2. Uses Gemini to generate a message for each slide
3. Caches each message by speaker notes content (not slide number)

Usage:
  python preload_presentation_messages.py \
    --pptx /path/to/deck.pptx \
    --languages en,zh

Notes:
  - Generates ONE message per unique speaker notes content
  - Cache key format: "v1:{language}:{hash(speaker_notes)}"
  - No slide numbers in cache - works even if slides reordered
  - VBA sends current slide's speaker notes for cache lookup
  - Duplicate speaker notes (same content) share same cache entry
"""

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from typing import Dict, List

from google.cloud import firestore
from google.adk.agents import config_agent_utils
from google.adk.runners import InMemoryRunner
from google.genai import types
from pptx import Presentation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def create_agent():
    """Create and return an ADK agent from YAML config."""
    # Get path to the agent config file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)
    config_file_path = os.path.join(
        backend_dir,
        "functions",
        "config",
        "presenter_agent",
        "root_agent.yaml"
    )
    
    # Load the agent from the config file using utility function
    return config_agent_utils.from_config(config_file_path)


def parse_languages(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _normalize_context(context: str) -> str:
    """Normalize context by trimming and collapsing whitespace."""
    if not context:
        return ""
    # Collapse all whitespace runs to a single space and strip ends
    return " ".join(str(context).split())


def _cache_key(language_code: str, context: str) -> str:
    """Build a stable, short cache key safe for Firestore doc IDs.

    Uses lowercase language + 12-char SHA256 of normalized context.
    Avoids very long document IDs and ensures consistent lookups.
    Must match the logic in firestore_utils.py
    """
    lang = (language_code or "").strip().lower() or "unknown"
    norm_ctx = _normalize_context(context)
    if not norm_ctx:
        return f"v1:{lang}:default"
    digest = hashlib.sha256(norm_ctx.encode("utf-8")).hexdigest()[:12]
    return f"v1:{lang}:{digest}"


def generate_message_from_notes(
    runner: InMemoryRunner,
    speaker_notes: str,
    language_code: str,
    slide_num: int
) -> str:
    """Generate a presentation message from speaker notes using Gemini.
    
    Args:
        runner: ADK runner instance
        speaker_notes: Raw speaker notes from all slides
        language_code: Target language (e.g., 'en', 'zh')
        slide_num: Slide number for logging (0 if combined notes)
        
    Returns:
        Generated message text
    """
    prompt = (
        f"Transform the following presentation speaker notes into a "
        f"clear, engaging message for students in {language_code} "
        f"language.\\n\\n"
        f"Speaker Notes:\\n{speaker_notes}\\n\\n"
        f"Generate a concise message (2-4 sentences) that captures the "
        f"key points. Return ONLY the message text, no explanations."
    )

    try:
        session_id = f"preload_slide{slide_num}_{language_code}"
        user_id = "preload_system"

        # Get or create session
        session = asyncio.run(
            runner.session_service.get_session(
                app_name='presentation_preloader',
                user_id=user_id,
                session_id=session_id,
            )
        )
        if session is None:
            session = asyncio.run(
                runner.session_service.create_session(
                    app_name='presentation_preloader',
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
        return result
    except Exception as e:
        logger.exception(
            "Failed to generate message for slide %d: %s",
            slide_num,
            e
        )
        return ""


def get_speaker_notes(prs: Presentation, slide_index: int) -> str:
    """Extract speaker notes from a slide.
    
    Args:
        prs: PowerPoint presentation object
        slide_index: 1-based slide index
        
    Returns:
        Speaker notes text, or empty string if no notes
    """
    if slide_index < 1 or slide_index > len(prs.slides):
        raise IndexError(
            f"slide index {slide_index} out of range (1..{len(prs.slides)})"
        )
    slide = prs.slides[slide_index - 1]
    
    # Access speaker notes
    if not slide.has_notes_slide:
        return ""
    
    notes_slide = slide.notes_slide
    if not notes_slide or not notes_slide.notes_text_frame:
        return ""
    
    return (notes_slide.notes_text_frame.text or "").strip()


def cache_message(
    db: firestore.Client,
    language_code: str,
    context: str,
    message: str
):
    """Write a cache entry for generate_presentation_message lookup."""
    cache_key = _cache_key(language_code, context)
    norm_ctx = _normalize_context(context)
    cache_ref = db.collection("xiaoice_presentation_cache").document(cache_key)
    cache_ref.set({
        "message": message,
        "language_code": (language_code or "").strip().lower(),
        "context": norm_ctx,
        "context_hash": cache_key.rsplit(":", 1)[-1],
        "updated_at": firestore.SERVER_TIMESTAMP
    })


def update_config(db: firestore.Client, messages: Dict[str, str]):
    """Update presentation_messages in config document."""
    doc_ref = db.collection("xiaoice_config").document("messages")
    doc = doc_ref.get()
    current = doc.to_dict() if doc.exists else {}
    merged = dict(current or {})
    merged["presentation_messages"] = messages
    merged["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(merged)


def main():
    parser = argparse.ArgumentParser(
        description="Preload presentation message cache from PPTX "
                    "speaker notes"
    )
    parser.add_argument("--pptx", required=True, help="Path to PPTX file")
    parser.add_argument(
        "--languages", default="en", help="Comma list, e.g. en,zh"
    )

    args = parser.parse_args()

    if not os.path.exists(args.pptx):
        raise FileNotFoundError(args.pptx)

    languages = parse_languages(args.languages)
    prs = Presentation(args.pptx)
    total_slides = len(prs.slides)
    
    # Initialize Gemini agent and runner
    logger.info("Initializing Gemini agent...")
    agent = create_agent()
    runner = InMemoryRunner(
        agent=agent,
        app_name='presentation_preloader',
    )
    
    db = firestore.Client(database="xiaoice")

    print(f"\nProcessing {total_slides} slides from {args.pptx}")
    print(f"Languages: {', '.join(languages)}")
    print("Using Gemini to generate messages...\n")

    cached_count = 0
    all_messages = {}

    # Process each slide individually
    for slide_idx in range(1, total_slides + 1):
        speaker_notes = get_speaker_notes(prs, slide_idx)
        
        if not speaker_notes:
            print(f"Slide {slide_idx}: No speaker notes - skipping")
            continue
        
        print(f"\nSlide {slide_idx}: Processing {len(speaker_notes)} "
              f"chars of notes")
        
        # Generate message for each language for this slide
        for lang in languages:
            logger.info(
                "Generating message for slide %d, language %s",
                slide_idx,
                lang
            )
            
            generated_message = generate_message_from_notes(
                runner,
                speaker_notes,
                lang,
                slide_idx
            )
            
            if not generated_message:
                logger.warning(
                    "Failed to generate message for slide %d, lang %s",
                    slide_idx,
                    lang
                )
                continue
            
            # Cache with speaker notes only (no slide number)
            # This way cache works even if slides are reordered
            cache_message(
                db,
                lang,
                speaker_notes,  # Just the notes content
                generated_message
            )
            cache_key = _cache_key(lang, speaker_notes)
            cached_count += 1
            
            # Store first 80 chars for display
            if len(generated_message) > 80:
                preview = generated_message[:80] + "..."
            else:
                preview = generated_message
            print(f"  [{lang}] Cached '{cache_key}'")
            print(f"       -> {preview}")
            
            # Build messages dict for config (keyed by lang:slideN)
            all_messages[f"{lang}:slide{slide_idx}"] = generated_message

    # Update config document
    if all_messages:
        update_config(db, all_messages)
        print(
            f"\n✓ Successfully cached {cached_count} AI-generated "
            f"message(s) across {len(languages)} language(s)"
        )
        print(
            f"✓ Updated presentation_messages in config with "
            f"{len(all_messages)} entry/entries"
        )
    else:
        print("\n⚠ No messages generated")


if __name__ == "__main__":
    main()
