# LangBridge (formerly Xiaoice Class Assistant)

A comprehensive system for integrating AI digital human interactions into classrooms and presentations. It consists of a serverless backend on Google Cloud Platform and client applications for real-time context monitoring.

## 📚 Documentation

Detailed documentation for each component can be found in the `docs/` directory:

- **[System Architecture](docs/ARCHITECTURE.md)**: High-level overview of the system, data flow, and security.
- **[Backend Documentation](docs/BACKEND.md)**: Details on Cloud Functions, API Gateway, and Infrastructure as Code (CDKTF).
- **[Python Monitor Client](docs/CLIENT_PYTHON.md)**: Guide for the desktop application that captures screen content and OCR.
- **[VBA PowerPoint Client](docs/CLIENT_VBA.md)**: Guide for the PowerPoint integration that pushes slide notes.
- **[Admin Tools & Caching](docs/ADMIN_TOOLS.md)**: Explanation of the content-based caching strategy and admin scripts.

### ✨ New in this version:

- **Multi-language support**: Now includes English, Mandarin, and Cantonese Text-to-Speech (TTS).
- **Course-level configuration**: Manage languages, voices, and content caching per course.
  - See [Admin Tools & Caching](docs/ADMIN_TOOLS.md) for how to set up courses.
  - See [VBA PowerPoint Client](docs/CLIENT_VBA.md) for how to configure your presentations with a `CourseID`.

## 🎬 Demo

[![LangBridge Demo 1](https://img.youtube.com/vi/JQs-Za-DAQ0/0.jpg)](https://www.youtube.com/shorts/JQs-Za-DAQ0)
[![LangBridge Demo 2](https://img.youtube.com/vi/s_MwaATKnzE/0.jpg)](https://www.youtube.com/shorts/s_MwaATKnzE)

## 🚀 Quick Start

### 1. Backend Deployment
The backend is managed via CDK for Terraform (CDKTF).

1.  Navigate to `backend/cdktf`.
2.  Copy `.env.template` to `.env` and fill in your GCP credentials.
3.  Run `npx cdktf deploy` to provision the infrastructure.
4.  Note the **API Gateway URL** from the output.

See [Backend Documentation](docs/BACKEND.md) for full details.

### 2. Setup Admin Tools & Create a Course

Before using the clients, set up the admin tools and create a demo course:

```bash
cd backend/admin_tools

# Setup Python environment and authenticate
./setup.sh
# OR manually:
source venv/bin/activate
gcloud auth application-default set-quota-project langbridge-presenter

# Create a demo course
python manage_courses.py update --id "demo" --title "Demo Course" --langs "en-US,zh-CN,yue-HK"

# Create an API key for a digital human
python create_api_key.py 12345678 "Cyrus"
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

## 🤝 Contributing

Please read the documentation in `docs/` before making changes. Ensure all new features are covered by tests.