# Speaker Note Generator - Implementation Plan (Final)

## Overview
A CLI tool that enhances PowerPoint presentations by automatically generating speaker notes using a **Supervisor-led Multi-Agent System** powered by Google ADK.

**Directory:** `backend/speaker_note_generator/`

## Inputs
1.  `--pptx`: Path to the PowerPoint file (Structure to modify).
2.  `--pdf`: Path to the PDF export of the same deck (Visual input for analysis).

## Architecture: Supervisor-Tool Pattern
Following official ADK Multi-Agent best practices, the **Supervisor Agent** is the primary intelligence. It decides *when* and *how* to use the other agents, which are exposed to it as **tools**.

### 1. Supervisor Agent (The Orchestrator)
*   **Type:** LLM Agent (Gemini).
*   **Role:** Manages the entire generation workflow for a slide.
*   **Capabilities:**
    *   Receives the slide's current state (image + existing text) and `Previous Slide Summary` (injected via prompt).
    *   Maintains a **consistent Session** throughout the presentation to manage multi-turn tool interactions.
    *   **Decides** whether to audit, analyze, or write.
    *   **Calls Tools:** `call_auditor`, `call_analyst`, `call_writer`.
*   **Goal:** Output the final, approved speaker note.

### 2. Worker Agents (The Tools)
These are specialized agents wrapped as Python tools callable by the Supervisor.

*   **Overviewer Agent (`pass_1`):**
    *   *Input:* All slide images.
    *   *Output:* Global Context (Narrative Arc, Persona).
*   **Auditor Tool (`call_auditor`):**
    *   *Input:* Existing note text.
    *   *Output:* `USEFUL` or `USELESS`.
*   **Analyst Tool (`call_analyst`):**
    *   *Input:* Slide Image ID (retrieves actual image from global registry).
    *   *Output:* Structured analysis (Topic, Details, Visuals).
*   **Writer Tool (`call_writer`):**
    *   *Input:* Analyst Output + Theme + Previous Context + Global Context.
    *   *Output:* Drafted script.
*   **Designer Tool (`call_designer`):**
    *   *Input:* Original Slide Image + Final Speaker Notes.
    *   *Output:* A high-fidelity Re-imagined Slide Image (saved to disk).

## Implementation Details

### Session Management Strategy
*   **Supervisor:** Uses a **single consistent session ID** (`supervisor_session`) for the entire run. This ensures the agent remembers its own plan (e.g., "I just audited this note, now I need to analyze the image") during the multi-turn tool execution loop for each slide.
*   **Workers:** Use **stateless/new sessions** for every call (`single_turn_session`) to ensure they have no memory of previous slides and focus solely on the immediate task.
*   **Context:** "Rolling Context" (Previous Slide Summary) is managed by the Python application (`main.py`) and explicitly injected into the Supervisor's prompt for every new slide.

### Core Logic (`main.py`)
1.  **Initialization:**
    *   Load PPTX (`python-pptx`) and PDF (`pymupdf`).
    *   Initialize `InMemoryRunner` for the Supervisor.
    *   Initialize `InMemoryRunner` instances for Auditor, Analyst, and Writer (used internally by tools).
    *   Register Python wrapper functions (`call_auditor`, `call_analyst`, `call_writer`) as tools for the Supervisor.
2.  **Pass 1 (Global Context):**
    *   Extract all images.
    *   Call `Overviewer` to get the master plan.
3.  **Pass 2 (Processing Loop):**
    *   **Image Handling:** Render PDF page to image and store in `IMAGE_REGISTRY` with a unique ID.
    *   **Input Construction:** Create a prompt for the Supervisor: *"Here is Slide X. Image ID: 'slide_X'. Existing notes: '...'. Previous Context: '...'. Global Context: '...'"*
    *   **Supervisor Execution:** The ADK Runner automatically handles the thinking loop:
        *   Supervisor -> Tool Call -> Python Function -> Worker Agent -> Result -> Supervisor.
    *   **Update:** Write the final text output to the PPTX slide.
    *   **Visualisation (New):** Call `Designer` agent with the original slide and the new note to generate a fresh slide visual. Save as `slide_X_reimagined.png`.
    *   **Context Update:** Update `previous_slide_summary` variable for the next iteration.
    *   **Cleanup:** Remove image from registry.
4.  **Finalization:** Save `[original_name]_enhanced.pptx`.

## Usage Example
```bash
cd backend/speaker_note_generator
./run.sh --pptx ../data/my_deck.pptx --pdf ../data/my_deck.pdf
```