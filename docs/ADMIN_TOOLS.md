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

**Language Codes**: These follow the **BCP-47** standard (e.g., `en-US`, `zh-CN`, `yue-HK`).

**Usage:**

```bash
# Create or Update a course
python manage_courses.py update --id "course_101" --title "Intro to AI" --langs "en-US,zh-CN,yue-HK"

# List all courses
python manage_courses.py list
```

### 2. `preload_presentation_messages` (Presentation Preloader)

**Location**: `backend/presentation-preloader/`

Pre-generates AI presentation messages from a PowerPoint file and caches them.

**Language Codes**: These follow the **BCP-47** standard (e.g., `en-US`, `zh-CN`, `yue-HK`).

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

### 3. `create_api_key.py` / `delete_api_key.py`

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
pip install virtualenv
python -m venv venv
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