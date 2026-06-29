# Admin Tools & Caching

The `backend/admin_tools` directory contains scripts for managing the system's cache, courses, and configuration.

## Content-Based Caching Logic

The system uses a robust caching strategy to ensure fast response times during presentations.

### The Problem
Using slide numbers as keys is brittle. Reordering slides invalidates the cache.

### The Solution
Use the **content** of the speaker notes to generate the cache key.

**Key Formula**: `v1:{language}:{hash(speaker_notes_content)}`

This ensures:
- **Reorder-Proof**: Content determines identity, not position.
- **Insert-Proof**: New slides don't shift existing IDs.
- **De-duplication**: Identical notes share the same cache.

```mermaid
flowchart TD
    A[Slide speaker notes] --> B[Normalize content]
    B --> C[Compute hash]
    C --> D[Build key v1:language:hash]
    D --> E{Key exists in Firestore?}
    E -->|Yes| F[Reuse cached message/audio]
    E -->|No| G[Generate new message + TTS]
    G --> H[Store in langbridge_presentation_cache]
```

## Tools

### 1. Excel Cache Editor (NEW)

Easily view and edit cached presentation messages using Excel. This allows content creators to refine AI-generated text without touching the database directly.

**Location**: `backend/admin_tools/`

#### Export to Excel
Export the current cache for a specific course to an `.xlsx` file.

```bash
# From backend/admin_tools/
python export_cache_to_excel.py --course-id "course_101" --output my_cache.xlsx
```

**Columns**:
- `Cache Key` (Do Not Edit): Unique ID.
- `Language`: The target language (e.g., `en`, `zh`).
- `Speaker Notes`: Context for reference.
- `Generated Message`: **Edit this column** to change what the AI says.

#### Import from Excel
Import the modified Excel file back into the system.

```bash
# From backend/admin_tools/
python import_cache_from_excel.py --course-id "course_101" --file my_cache.xlsx
```

**What happens on import?**
1. The script compares the Excel message with the database.
2. If the text has changed:
   - Updates the message in Firestore.
   - **Automatically regenerates** the TTS audio (MP3).
   - Uploads the new audio to Cloud Storage.
   - Updates the `audio_url` in the cache.

```mermaid
sequenceDiagram
    participant User as Content Editor
    participant XLSX as Excel File
    participant Tool as import_cache_from_excel.py
    participant FS as Firestore
    participant TTS as Text-to-Speech
    participant GCS as Cloud Storage

    User->>XLSX: Edit "Generated Message"
    User->>Tool: Run import command
    Tool->>FS: Compare with existing cache
    alt Message changed
        Tool->>TTS: Synthesize new audio
        Tool->>GCS: Upload MP3
        Tool->>FS: Update text + audio_url
    else No change
        Tool->>FS: Skip update
    end
```

### 2. `manage_courses.py`

Manages Course Configurations (languages, voices, etc.).

**Language Codes**: These follow the **BCP-47** standard (e.g., `en-US`, `zh-CN`, `yue-HK`).

**Usage:**

```bash
# Create or Update a course
python manage_courses.py update --id "course_101" --title "Intro to AI" --langs "en-US,zh-CN,yue-HK"

# List all courses
python manage_courses.py list
```

### 3. `preload_presentation_messages` (Presentation Preloader)

**Location**: `backend/presentation-preloader/`

Pre-generates AI presentation messages from a PowerPoint file and caches them.

**Usage:**

```bash
cd backend/presentation-preloader

# Install dependencies (first time)
pip install -r requirements.txt

# Update configuration (if infrastructure changed)
./update_config.sh

# Run the tool
# Using Course Config (Recommended)
python main.py --pptx /path/to/deck.pptx --course-id "course_101"

# Manual Language Selection
python main.py --pptx /path/to/deck.pptx --languages "en-US,zh-CN,yue-HK"
```

**Process**:
1. Reads the `.pptx` file.
2. Extracts speaker notes from every slide.
3. Computes the hash of the notes.
4. Checks Firestore (`langbridge_presentation_cache`). If missing, calls the AI to generate a "presentation script" or summary.
5. Saves the result to Firestore (tagged with `course_id`).
6. Generates and uploads TTS audio (using course-specific voice settings).

### 4. `create_api_key.py` / `delete_api_key.py`

**Purpose**: Manage API keys for the API Gateway.

**Usage**:
```bash
# Create an API key for a digital human
python create_api_key.py <digital_human_id> <name>

# Example
python create_api_key.py 12345678 "Cyrus"

# Delete an API key
python delete_api_key.py <api_key_string>
```

**Note**: The API key will be automatically added to Firestore and restricted to the configured API service. The key details are saved to a JSON file in the current directory.

## Environment Setup

The admin tools require a Python environment with dependencies installed and proper GCP authentication configured.

### Quick Setup

```bash
cd backend/admin_tools

# Option 1: Use the automated setup script
./setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Application Default Credentials quota project
gcloud auth application-default set-quota-project langbridge-presenter
```

### Authentication Requirements

⚠️ **Important**: Before running any admin tools, ensure you have:

1. **Authenticated with GCP**: Run `gcloud auth login` if you haven't already
2. **Set the correct project**: `gcloud config set project langbridge-presenter`
3. **Configured ADC quota project**: `gcloud auth application-default set-quota-project langbridge-presenter`

The quota project ensures that API calls are billed to the correct GCP project, especially important when working with multiple projects or when the default credentials point to a different/deleted project.
