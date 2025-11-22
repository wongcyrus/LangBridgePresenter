# Speaker Note Generator

This tool automatically generates or enhances speaker notes for PowerPoint presentations using a **Supervisor-led Multi-Agent System** powered by Google ADK.

It takes a PowerPoint (`.pptx`) and its corresponding PDF export (`.pdf`) as input. The PDF provides visual context for AI analysis, while the PPTX is updated with the generated speaker notes.

## Architecture
The system employs a multi-agent approach:
1.  **Supervisor Agent:** Orchestrates the workflow for each slide, deciding whether to audit existing notes, analyze the slide's visual content, or generate new speaker notes. It maintains the overall context of the presentation.
2.  **Auditor Agent:** Evaluates the quality and usefulness of any existing speaker notes.
3.  **Analyst Agent:** Analyzes the visual content of a slide (from the PDF image) to extract key topics, details, and visual descriptions.
4.  **Writer Agent:** Crafts coherent, first-person speaker notes based on the Analyst's insights and the overall presentation context.

## Setup
1.  Navigate to the tool's directory:
    ```bash
    cd backend/speaker_note_generator
    ```
2.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Ensure you have valid Google Cloud credentials configured for your environment (e.g., via `gcloud auth application-default login` or by setting `GOOGLE_APPLICATION_CREDENTIALS`).

## Usage
Run the `run.sh` script, providing the paths to your PPTX and PDF files. You can optionally include a `--course-id` to fetch additional context from Firestore.

```bash
./run.sh --pptx /path/to/your/presentation.pptx --pdf /path/to/your/presentation.pdf [--course-id your-course-id]
```

**Arguments:**
*   `--pptx`: Path to the input PowerPoint (`.pptx`) file.
*   `--pdf`: Path to the corresponding PDF export of the presentation.
*   `--course-id` (Optional): A Firestore Course ID. If provided, the tool will attempt to fetch course details (like name or description) to provide more relevant thematic context to the agents.

## Output
The tool will generate a new PowerPoint file with `_enhanced.pptx` appended to the original filename (e.g., `my_presentation_enhanced.pptx`). This new file will contain updated or newly generated speaker notes for each slide.

Console output will show the progress, including agent decisions, analysis summaries, and generated notes.

## Context Handling
*   **Rolling Context:** The Supervisor Agent maintains a "rolling context" by being aware of the previous slide's generated note. This helps in creating smooth transitions between slides.
*   **Presentation Theme:** The overall theme of the presentation is either a generic default or derived from the `--course-id` (if provided), helping agents align their output with the subject matter.

