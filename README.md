# LangBridge Presenter

A comprehensive system for integrating AI digital human interactions into classrooms and presentations. It consists of a serverless backend on Google Cloud Platform and client applications for real-time context monitoring.

## 📚 Documentation

Detailed documentation for each component can be found in the `docs/` directory:

- **[System Architecture](docs/ARCHITECTURE.md)**: High-level overview of the system, data flow, and security.
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Step-by-step guide to deploying the full stack (Backend & Web Client).
- **[Backend Documentation](docs/BACKEND.md)**: Details on Cloud Functions, API Gateway, and Infrastructure as Code (CDK Terrain / CDKTN).
- **[Python Monitor Client](docs/CLIENT_PYTHON.md)**: Guide for the desktop application that captures screen content and OCR.
- **[VBA PowerPoint Client](docs/CLIENT_VBA.md)**: Guide for the PowerPoint integration that pushes slide notes.
- **[Admin Tools & Caching](docs/ADMIN_TOOLS.md)**: Explanation of the content-based caching strategy and admin scripts.

### ✨ New in this version:

- **Multi-language support**: Now includes English, Mandarin, and Cantonese Text-to-Speech (TTS).
- **Excel Cache Editor**: Easily export, edit, and re-import presentation messages using Excel to refine AI content.
- **Course-level configuration**: Manage languages, voices, and content caching per course.
  - See [Admin Tools & Caching](docs/ADMIN_TOOLS.md) for how to set up courses.
  - See [VBA PowerPoint Client](docs/CLIENT_VBA.md) for how to configure your presentations with a `CourseID`.
- **Multiple Presenter Support**: Specify comma-separated presenter IDs to enable collaborative presentations with multiple AI agents sharing the same context.
- **Slide Narration Mode**: Play the pre-generated MP3 for the current slide, with keyboard/touch controls for low-vision users.
- **Keyboard Shortcuts**: Use Alt+N, Alt+R, Alt+L, and Alt+←/→ for narration and slide control.

## 🎬 Demo

[![LangBridge Demo 1](https://img.youtube.com/vi/JQs-Za-DAQ0/0.jpg)](https://www.youtube.com/shorts/JQs-Za-DAQ0)
[![LangBridge Demo 2](https://img.youtube.com/vi/s_MwaATKnzE/0.jpg)](https://www.youtube.com/shorts/s_MwaATKnzE)

## 🚀 Quick Start

### 1. Deploy in 3 phases

1.  **Phase 1 – Infra + Hosting**  
    Copy `.env.template` to `.env` (or `.env.dev.template` to `.env.dev`) under `backend/cdktf/`, then run:

    ```bash
    ./deploy.sh --env-file backend/cdktf/.env.dev
    ```

2.  **Phase 2 – Client Auth setup**  
    Open Firebase Console for the client project, initialize Authentication, then run:

    ```bash
    python3 backend/admin_tools/bootstrap_client_auth.py --outputs-file backend/cdktf_outputs.json
    ```

3.  **Phase 3 – Seed content**  
    Seed showcase data (text/audio/visual):

    ```bash
    PYTHONPATH=backend/admin_tools \
    backend/.venv/bin/python backend/seeds/seed_course_content.py \
      --course-id showcase \
      --course-title Showcase \
      --data-dir generate \
      --languages en-US zh-CN yue-HK
    ```

See [Deployment Guide](docs/DEPLOYMENT.md) for comprehensive instructions and troubleshooting.

### 2. Setup Admin Tools & Create a Course

After running `./deploy.sh`, set up the admin tools and create a demo course:

```bash
cd backend/admin_tools

# Setup Python environment and authenticate
./setup.sh

# Create a demo course (explicit project target)
python manage_courses.py --project-id langbridge-presenter-d2 --database langbridge update --id "demo" --title "Demo Course" --langs "en-US,zh-CN,yue-HK"

# Create a presenter
python manage_presenters.py --project-id langbridge-presenter-d2 --database langbridge update --id "summer" --name "Summer" --language "en-US" --background "Friendly AI assistant"

# Create an API key for a digital human
python create_api_key.py 12345678 "Cyrus" --project-id langbridge-presenter-d2 --database langbridge --api-service "<api-service-name>"
```

See [Admin Tools & Caching](docs/ADMIN_TOOLS.md) for more details.

### 3. Client Setup

#### Python Window Monitor
Captures your screen content to provide visual context to the AI.

```bash
cd client/python
python setup.py
# Activate venv
python window_monitor.py
```

See [Python Monitor Docs](docs/CLIENT_PYTHON.md).

#### PowerPoint Integration (VBA)
Pushes speaker notes to the AI as you navigate slides.

1.  Open your presentation in PowerPoint.
2.  Import the VBA files from `client/vba`.
3.  Add your API Key to `api_config.txt`.

See [VBA Client Docs](docs/CLIENT_VBA.md).

## 📂 Project Structure

```
xiaoice_class_assistant/
├── backend/              # Serverless API infrastructure
│   ├── admin_tools/      # Scripts for cache preloading & key management
│   ├── cdktf/            # Infrastructure as Code (Terraform)
│   └── functions/        # Cloud Functions (Chat, Welcome, Config, etc.)
├── client/               # Client-side context monitors
│   ├── python/           # Desktop screen monitor (OCR)
│   └── vba/              # PowerPoint integration
└── docs/                 # Detailed project documentation
```

## 🧪 Testing

Run the backend integration tests:

```bash
cd backend/tests
./run_tests.sh
```

The `run_tests.sh` script will automatically sync configurations (including generating `.env.test`) before running pytest.

## 🤝 Contributing

Please read the documentation in `docs/` before making changes. Ensure all new features are covered by tests.