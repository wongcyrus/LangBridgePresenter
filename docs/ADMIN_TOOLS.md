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

## Tools

### 1. `manage_courses.py`

Manages Course Configurations (languages, voices, etc.).

**Usage:**

```bash
# Create or Update a course
python manage_courses.py update --id "course_101" --title "Intro to AI" --langs "en-US,zh-CN,yue-HK"

# List all courses
python manage_courses.py list
```

### 2. `preload_presentation_messages.py`

Pre-generates AI presentation messages from a PowerPoint file and caches them.

**Usage:**

```bash
# Using Course Config (Recommended)
python preload_presentation_messages.py --pptx /path/to/deck.pptx --course-id "course_101"

# Manual Language Selection (Legacy)
python preload_presentation_messages.py --pptx /path/to/deck.pptx --languages "en,zh"
```

**Process**:
1. Reads the `.pptx` file.
2. Extracts speaker notes from every slide.
3. Computes the hash of the notes.
4. Checks Firestore. If missing, calls the AI to generate a "presentation script" or summary.
5. Saves the result to Firestore (tagged with `course_id`).
6. Generates and uploads TTS audio (using course-specific voice settings).

### 3. `create_api_key.py` / `delete_api_key.py`

**Purpose**: Manage API keys for the API Gateway.

**Usage**:
```bash
python create_api_key.py --project <project_id> --name <key_name>
```

## Environment Setup

The admin tools require a Python environment with dependencies installed:

```bash
cd backend/admin_tools
pip install -r requirements.txt
```