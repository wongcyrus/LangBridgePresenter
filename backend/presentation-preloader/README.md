# Presentation Preloader

This tool pre-generates presentation messages from PPTX speaker notes using Gemini and caches them for the LangBridge application. It also generates speech files using Google Text-to-Speech.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Ensure you have valid Google Cloud credentials.

## Usage

Run the script pointing to your PPTX file:

```bash
python main.py --pptx /path/to/deck.pptx --languages en,zh
```

Arguments:
- `--pptx`: Path to the PowerPoint file.
- `--languages`: Comma-separated list of languages (e.g., `en,zh`).
- `--course-id`: Optional Course ID to use configuration from Firestore.

## Configuration

- `config.py`: Contains project configuration (bucket names, etc.).
- `agent_config/root_agent.yaml`: Configuration for the Gemini agent.
- `utils/course_utils.py`: Utilities for fetching course configuration.

To automatically update `config.py` with the latest Terraform outputs, run:

```bash
./update_config.sh
```
