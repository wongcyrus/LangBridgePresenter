#!/usr/bin/env python3
"""
Speaker Note Generator
Enhances PowerPoint presentations by generating speaker notes using a Supervisor-Tool Multi-Agent System.

Architecture: Supervisor Agent (Orchestrator) -> Tool Functions -> Worker Agents
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Callable, Dict, Any

import pymupdf  # fitz
from PIL import Image
from pptx import Presentation

from google.adk.agents import config_agent_utils
from google.adk.runners import InMemoryRunner
from google.genai import types

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global registry for images to be accessed by tools
# This avoids passing heavy image data through string-based tool arguments
IMAGE_REGISTRY: Dict[str, Image.Image] = {}

class WorkerAgents:
    """Manages the specialized worker agents (Auditor, Analyst, Writer)."""
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.auditor_runner = self._create_runner("auditor.yaml", "auditor")
        self.analyst_runner = self._create_runner("analyst.yaml", "analyst")
        self.writer_runner = self._create_runner("writer.yaml", "writer")

    def _create_runner(self, config_file: str, app_name: str) -> InMemoryRunner:
        path = os.path.join(self.config_dir, config_file)
        agent = config_agent_utils.from_config(path)
        return InMemoryRunner(agent=agent, app_name=app_name)

    async def run_simple_agent(self, runner: InMemoryRunner, prompt: str, image: Image.Image = None) -> str:
        """Helper to run a stateless single-turn agent."""
        user_id = "system_user"
        
        parts = [types.Part.from_text(text=prompt)]
        if image:
            parts.append(types.Part.from_image(image=image))

        content = types.Content(role='user', parts=parts)
        
        # Create new session for statelessness
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
        )
        
        response_text = ""
        try:
            for event in runner.run(
                user_id=user_id,
                session_id=session.session_id,
                new_message=content,
            ):
                if getattr(event, "content", None) and event.content.parts:
                    part = event.content.parts[0]
                    text = getattr(part, "text", "") or ""
                    response_text += text
        except Exception as e:
            logger.error(f"Error running agent {runner.app_name}: {e}")
            return f"Error: {e}"
            
        return response_text.strip()


# --- Tool Functions Exposed to Supervisor ---

workers: WorkerAgents = None

async def call_auditor(note_text: str) -> str:
    """Tool: Checks if existing notes are useful."""
    logger.info(f"[Tool] call_auditor invoked. Note length: {len(note_text)}")
    prompt = f"Existing Note: \"{note_text}\"\n\nEvaluate if this is USEFUL or USELESS. Return JSON."
    return await workers.run_simple_agent(workers.auditor_runner, prompt)

async def call_analyst(image_id: str) -> str:
    """Tool: Analyzes the slide image."""
    logger.info(f"[Tool] call_analyst invoked for image_id: {image_id}")
    image = IMAGE_REGISTRY.get(image_id)
    if not image:
        return "Error: Image not found."
    
    prompt = "Analyze this slide image."
    return await workers.run_simple_agent(workers.analyst_runner, prompt, image=image)

async def call_writer(analysis: str, previous_context: str, theme: str) -> str:
    """Tool: Writes the script."""
    logger.info("[Tool] call_writer invoked.")
    prompt = (
        f"SLIDE_ANALYSIS:\n{analysis}\n\n"
        f"PRESENTATION_THEME: {theme}\n"
        f"PREVIOUS_CONTEXT: {previous_context}\n"
    )
    return await workers.run_simple_agent(workers.writer_runner, prompt)


async def process_presentation(pptx_path: str, pdf_path: str, course_id: str = None):
    global workers
    
    logger.info(f"Processing PPTX: {pptx_path}")
    
    # Load files
    prs = Presentation(pptx_path)
    pdf_doc = pymupdf.open(pdf_path)
    limit = min(len(prs.slides), len(pdf_doc))
    
    # Initialize Agents
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config")
    workers = WorkerAgents(config_dir)
    
    # Initialize Supervisor
    supervisor_agent = config_agent_utils.from_config(os.path.join(config_dir, "supervisor.yaml"))
    
    # Register Tools
    tools_map = {
        "call_auditor": call_auditor,
        "call_analyst": call_analyst,
        "call_writer": call_writer
    }
    
    supervisor_runner = InMemoryRunner(
        agent=supervisor_agent, 
        app_name="supervisor",
        tools=tools_map
    )

    # Global Context
    presentation_theme = "General Presentation" 
    if course_id:
        try:
            # Dynamically import to avoid circular imports if utils not in path
            sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from presentation_preloader.utils import course_utils
            course_config = course_utils.get_course_config(course_id)
            if course_config:
                # Prefer 'description' then 'name', fallback to ID
                presentation_theme = course_config.get("description") or course_config.get("name") or f"Course {course_id}"
                logger.info(f"Set Presentation Theme from Course: {presentation_theme}")
        except Exception as e:
            logger.warning(f"Failed to fetch course config for {course_id}: {e}")

    previous_slide_summary = "Start of presentation."

    user_id = "supervisor_user"
    session_id = "supervisor_session" # Consistent session for the entire presentation
    
    # Create Supervisor Session
    await supervisor_runner.session_service.create_session(
        app_name="supervisor",
        user_id=user_id,
        session_id=session_id
    )

    for i in range(limit):
        slide_idx = i + 1
        slide = prs.slides[i]
        pdf_page = pdf_doc[i]
        
        logger.info(f"--- Processing Slide {slide_idx} ---")
        
        # 1. Setup Slide Context
        existing_notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
             existing_notes = slide.notes_slide.notes_text_frame.text.strip()

        # Register Image
        image_id = f"slide_{slide_idx}"
        pix = pdf_page.get_pixmap(dpi=150)
        IMAGE_REGISTRY[image_id] = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 2. Prompt Supervisor
        supervisor_prompt = (
            f"Here is Slide {slide_idx}.\n"
            f"Existing Notes: \"{existing_notes}\"\n"
            f"Image ID: \"{image_id}\"\n"
            f"Previous Slide Summary: \"{previous_slide_summary}\"\n"
            f"Theme: \"{presentation_theme}\"\n\n"
            f"Please proceed with the workflow."
        )

        content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=supervisor_prompt)]
        )

        # 3. Run Supervisor Loop
        final_response = ""
        
        # The runner handles tool calls internally if configured correctly with 'tools' arg
        for event in supervisor_runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if getattr(event, "content", None) and event.content.parts:
                 part = event.content.parts[0]
                 text = getattr(part, "text", "") or ""
                 final_response += text

        final_response = final_response.strip()
        logger.info(f"Final Note for Slide {slide_idx}: {final_response[:50]}...")
        
        # 4. Update PPTX
        if not slide.has_notes_slide:
             # Force creation of notes slide if possible, otherwise skip for now
             # In older python-pptx, accessing .notes_slide creates it.
             pass
        try:
            slide.notes_slide.notes_text_frame.text = final_response
        except Exception as e:
            logger.error(f"Could not write note: {e}")
            
        # 5. Update Context
        previous_slide_summary = final_response[:200] # Simple summary for now

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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pptx) or not os.path.exists(args.pdf):
        print("Error: Input files not found.")
        return

    asyncio.run(process_presentation(args.pptx, args.pdf, args.course_id))

if __name__ == "__main__":
    main()