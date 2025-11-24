#!/usr/bin/env python3
"""
Speaker Note Generator
Enhances PowerPoint presentations by generating speaker notes using a Supervisor-Tool Multi-Agent System.

Refactored to use Python-based Agent definitions.
"""

import argparse
import asyncio
import logging
import os
import sys
import io
import json
import hashlib
import tempfile
from typing import Dict, Any, List

import pymupdf  # fitz
from PIL import Image
from pptx import Presentation

from google.adk.runners import InMemoryRunner
from google.genai import types
from google.adk.agents import LlmAgent

# Import Agents
# Ensure the path includes the current directory to find 'agents'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.supervisor import supervisor_agent
from agents.analyst import analyst_agent
from agents.overviewer import overviewer_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global registry for images
IMAGE_REGISTRY: Dict[str, Image.Image] = {}

def _create_image_part(image: Image.Image) -> types.Part:
    """Helper to create a Part object from a PIL Image safely."""
    if hasattr(types.Part, 'from_image'):
        return types.Part.from_image(image=image)
    else:
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        img_bytes = buf.getvalue()
        if hasattr(types.Part, 'from_bytes'):
            return types.Part.from_bytes(
                data=img_bytes,
                mime_type='image/png'
            )
        else:
            return types.Part(
                mime_type='image/png',
                data=img_bytes
            )

async def run_stateless_agent(
    agent: LlmAgent,
    prompt: str,
    images: List[Image.Image] = None,
) -> str:
    """Helper to run a stateless single-turn agent."""
    runner = InMemoryRunner(agent=agent, app_name=agent.name)
    user_id = "system_user"
    
    parts = [types.Part.from_text(text=prompt)]
    if images:
        for img in images:
            try:
                parts.append(_create_image_part(img))
            except Exception as e:
                logger.error(f"Failed to attach image part: {e}")

    content = types.Content(role='user', parts=parts)
    
    # Create new session for statelessness
    session = await runner.session_service.create_session(
        app_name=agent.name,
        user_id=user_id,
    )
    # Safely determine session id across possible ADK versions
    def _extract_session_id(sess):
        for attr in ("session_id", "id"):
            if hasattr(sess, attr):
                return getattr(sess, attr)
        nested = getattr(sess, "session", None)
        if nested:
            for attr in ("session_id", "id"):
                if hasattr(nested, attr):
                    return getattr(nested, attr)
        # As a last resort, look for any attribute ending with '_id'
        for name in dir(sess):
            if name.endswith('_id'):
                return getattr(sess, name)
        raise AttributeError("Could not determine session id on object: " + repr(sess))

    try:
        resolved_session_id = _extract_session_id(session)
    except Exception as sid_err:
        logger.error(f"Failed to extract session id: {sid_err}; falling back to generated id.")
        resolved_session_id = f"fallback_{user_id}"

    print(f"\n┌── [Agent: {agent.name}]")
    print(f"│ Task: {prompt.strip()[:500].replace(chr(10), ' ') + ('...' if len(prompt) > 500 else '')}")
    if images:
        print(f"│ [{len(images)} Images Attached]")

    response_text = ""
    try:
        # Run agent
        for event in runner.run(
            user_id=user_id,
            session_id=resolved_session_id,
            new_message=content,
        ):
            if getattr(event, "content", None) and event.content.parts:
                part = event.content.parts[0]
                text = getattr(part, "text", "") or ""
                response_text += text
    except Exception as e:
        logger.error(f"Error running agent {agent.name}: {e}")
        return f"Error: {e}"
    
    print(f"└-> Response: {response_text.strip()[:500].replace(chr(10), ' ') + ('...' if len(response_text) > 500 else '')}")
    return response_text.strip()

# Tool wrapper for Analyst
async def call_analyst(image_id: str) -> str:
    """Tool: Analyzes the slide image."""
    logger.info(f"[Tool] call_analyst invoked for image_id: {image_id}")
    image = IMAGE_REGISTRY.get(image_id)
    if not image:
        return "Error: Image not found."
    
    prompt_text = "Analyze this slide image."
    return await run_stateless_agent(analyst_agent, prompt_text, images=[image])

async def call_writer(
    analysis: str,
    previous_context: str,
    theme: str,
    global_context: str = "No global context provided." 
) -> str:
    """Tool: Writes the script."""
    logger.info("[Tool] call_writer invoked.")
    prompt = (
        f"SLIDE_ANALYSIS:\n{analysis}\n\n"
        f"PRESENTATION_THEME: {theme}\n"
        f"PREVIOUS_CONTEXT: {previous_context}\n"
        f"GLOBAL_CONTEXT: {global_context}\n"
    )
    return await run_stateless_agent(writer_agent, prompt)


async def process_presentation(
    pptx_path: str,
    pdf_path: str,
    course_id: str = None,
):
    
    logger.info(f"Processing PPTX: {pptx_path}")
    
    # Load files
    prs = Presentation(pptx_path)
    pdf_doc = pymupdf.open(pdf_path)
    limit = min(len(prs.slides), len(pdf_doc))

    # 0. PASS 1: Global Context Generation
    logger.info("--- Pass 1: Generating Global Context ---")
    all_images = []
    for i in range(limit):
        pix = pdf_doc[i].get_pixmap(dpi=75) # Lower DPI for overview to save bandwidth/tokens
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        all_images.append(img)
    
    global_context = await run_stateless_agent(
        overviewer_agent,
        "Here are the slides for the entire presentation. Analyze them.",
        images=all_images
    )
    logger.info(f"Global Context Generated: {len(global_context)} chars")
    
    # Configure Supervisor Tools
    # Assign list of functions directly to override defaults and ensure new signatures are used
    supervisor_agent.tools = [call_analyst, call_writer]

    # Initialize Supervisor Runner
    supervisor_runner = InMemoryRunner(
        agent=supervisor_agent,
        app_name="supervisor"
    )

    # Global Context
    presentation_theme = "General Presentation"
    if course_id:
        try:
            # Dynamically import to avoid circular imports
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            if project_root not in sys.path:
                sys.path.append(project_root)
            from presentation_preloader.utils import course_utils
            course_config = course_utils.get_course_config(course_id)
            if course_config:
                presentation_theme = (
                    course_config.get("description")
                    or course_config.get("name")
                    or f"Course {course_id}"
                )
                logger.info(
                    f"Set Presentation Theme from Course: {presentation_theme}"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch course config for {course_id}: {e}")

    previous_slide_summary = "Start of presentation."

    user_id = "supervisor_user"
    session_id = "supervisor_session" 
    
    # Create Supervisor Session
    await supervisor_runner.session_service.create_session(
        app_name="supervisor",
        user_id=user_id,
        session_id=session_id
    )

    # --- Progress Tracking Setup ---
    progress_file = os.environ.get("SPEAKER_NOTE_PROGRESS_FILE") or os.getenv("SPEAKER_NOTE_PROGRESS_FILE")
    # Allow overriding via environment; fallback default next to PPTX
    if not progress_file:
        progress_file = os.path.join(os.path.dirname(pptx_path), "speaker_note_progress.json")
    retry_errors = os.environ.get("SPEAKER_NOTE_RETRY_ERRORS", "false").lower() == "true"

    def load_progress(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {"slides": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load progress file {path}: {e}")
            return {"slides": {}}

    def save_progress(path: str, data: Dict[str, Any]):
        """Persist progress atomically; ensure temp file created on same volume.

        Windows cannot move files across different drives with os.replace; creating
        the temporary file in the target directory avoids WinError 17.
        """
        try:
            target_dir = os.path.dirname(path) or "."
            tmp_fd, tmp_path = tempfile.mkstemp(
                prefix="sn_prog_",
                suffix=".json",
                dir=target_dir,
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception as e:
            logger.error(f"Failed to save progress file {path}: {e}")

    def slide_key(index: int, notes: str) -> str:
        h = hashlib.sha256((notes or "").encode("utf-8")).hexdigest()[:8]
        return f"slide_{index}_{h}"

    progress = load_progress(progress_file)
    # Save Global Context to progress for debugging/resuming
    if "global_context" not in progress:
        progress["global_context"] = global_context
        save_progress(progress_file, progress)
    else:
        # Use cached global context if available and valid
        if progress["global_context"] and len(progress["global_context"]) > 50:
             logger.info("Using cached Global Context from progress file.")
             global_context = progress["global_context"]

    logger.info(f"Using progress file: {progress_file} (retry_errors={retry_errors})")

    # 1. Pass 2: Slide Loop
    for i in range(limit):
        slide_idx = i + 1
        slide = prs.slides[i]
        pdf_page = pdf_doc[i]
        
        logger.info(f"--- Processing Slide {slide_idx} ---")
        
        # 1. Setup Slide Context
        existing_notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            existing_notes = slide.notes_slide.notes_text_frame.text.strip()

        skey = slide_key(slide_idx, existing_notes)
        entry = progress["slides"].get(skey)

        # Skip slide if already successful and not retrying errors
        if entry and entry.get("status") == "success" and not retry_errors:
            final_response = entry.get("note", "")
            logger.info(f"Skipping slide {slide_idx}; already generated (progress file)")
            # Ensure note written (in case PPTX was reverted)
            try:
                if not slide.has_notes_slide:
                    slide.notes_slide  # may initialize
                slide.notes_slide.notes_text_frame.text = final_response
            except Exception as e:
                logger.error(f"Could not reapply saved note: {e}")
            previous_slide_summary = final_response[:200]
            continue

        # Register Image
        image_id = f"slide_{slide_idx}"
        pix = pdf_page.get_pixmap(dpi=150)
        IMAGE_REGISTRY[image_id] = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 2. Prompt Supervisor
        # Inject GLOBAL CONTEXT here
        supervisor_prompt = (
            f"Here is Slide {slide_idx}.\n"
            f"Existing Notes: \"{existing_notes}\"\n"
            f"Image ID: \"{image_id}\"\n"
            f"Previous Slide Summary: \"{previous_slide_summary}\"\n"
            f"Theme: \"{presentation_theme}\"\n"
            f"Global Context: \"{global_context}\"\n\n"
            f"Please proceed with the workflow."
        )

        content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=supervisor_prompt)]
        )

        # 3. Run Supervisor Loop
        final_response = ""
        
        try:
            for event in supervisor_runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                if getattr(event, "content", None) and event.content.parts:
                    for part in event.content.parts:
                        # Check for Function Call
                        fn_call = getattr(part, "function_call", None)
                        if fn_call:
                            print(f"\n[Supervisor] 📞 calling tool: {fn_call.name}")
                            # print(f"             Args: {fn_call.args}") 

                        # Check for Text
                        text = getattr(part, "text", "") or ""
                        final_response += text
        except Exception as e:
            logger.error(f"Error in supervisor loop: {e}")

        final_response = final_response.strip()
        status = "success"
        if not final_response or final_response.lower().startswith("error:"):
            status = "error"
        logger.info(f"Final Note for Slide {slide_idx}: {final_response[:50]}... (status={status})")
        
        # 4. Update PPTX
        if not slide.has_notes_slide:
             try:
                 slide.notes_slide # This might create it in some versions or fail
             except:
                 pass # Handling logic depends on pptx version

        try:
            slide.notes_slide.notes_text_frame.text = final_response
        except Exception as e:
            logger.error(f"Could not write note: {e}")
            
        # 5. Update Context
        previous_slide_summary = final_response[:200]

        # Update progress entry and persist after each slide
        progress["slides"][skey] = {
            "slide_index": slide_idx,
            "existing_notes_hash": skey.split("_")[-1],
            "original_notes": existing_notes,
            "note": final_response,
            "status": status,
        }
        save_progress(progress_file, progress)

        # Cleanup Image
        del IMAGE_REGISTRY[image_id]

    # Save
    output_path = pptx_path.replace(".pptx", "_enhanced.pptx")
    prs.save(output_path)
    logger.info(f"Saved enhanced deck to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate Speaker Notes with Supervisor Agent")
    parser.add_argument("--pptx", required=True, help="Path to input PPTX")
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    parser.add_argument("--course-id", help="Optional: Course ID to fetch theme context")
    parser.add_argument("--progress-file", help="Override path for progress JSON file")
    parser.add_argument("--retry-errors", action="store_true", help="Retry slides previously marked as error")

    args = parser.parse_args()

    if not os.path.exists(args.pptx) or not os.path.exists(args.pdf):
        print("Error: Input files not found.")
        return

    # Allow CLI args to override environment defaults
    if args.progress_file:
        os.environ["SPEAKER_NOTE_PROGRESS_FILE"] = args.progress_file
    if args.retry_errors:
        os.environ["SPEAKER_NOTE_RETRY_ERRORS"] = "true"

    asyncio.run(process_presentation(args.pptx, args.pdf, args.course_id))

if __name__ == "__main__":
    main()