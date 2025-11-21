# Xiaoice Class Assistant

A comprehensive system for integrating AI digital human interactions into classrooms and presentations. It consists of a serverless backend on Google Cloud Platform and client applications for real-time context monitoring.

## 📚 Documentation

Detailed documentation for each component can be found in the `docs/` directory:

- **[System Architecture](docs/ARCHITECTURE.md)**: High-level overview of the system, data flow, and security.
- **[Backend Documentation](docs/BACKEND.md)**: Details on Cloud Functions, API Gateway, and Infrastructure as Code (CDKTF).
- **[Python Monitor Client](docs/CLIENT_PYTHON.md)**: Guide for the desktop application that captures screen content and OCR.
- **[VBA PowerPoint Client](docs/CLIENT_VBA.md)**: Guide for the PowerPoint integration that pushes slide notes.
- **[Admin Tools & Caching](docs/ADMIN_TOOLS.md)**: Explanation of the content-based caching strategy and admin scripts.

## 🎬 Demo

- [Xiaoice Class Assistant Demo 1](https://youtube.com/shorts/JQs-Za-DAQ0?feature=share)
- [Xiaoice Class Assistant Demo 2](https://youtube.com/shorts/s_MwaATKnzE?feature=share)

## 🚀 Quick Start

### 1. Backend Deployment
The backend is managed via CDK for Terraform (CDKTF).

1.  Navigate to `backend/cdktf`.
2.  Copy `.env.template` to `.env` and fill in your GCP credentials.
3.  Run `npx cdktf deploy` to provision the infrastructure.
4.  Note the **API Gateway URL** from the output.

See [Backend Documentation](docs/BACKEND.md) for full details.

### 2. Client Setup

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