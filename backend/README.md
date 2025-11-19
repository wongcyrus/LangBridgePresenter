# Xiaoice Class Assistant

GCP Cloud Functions implementation of Xiaoice API endpoints using CDKTF for deployment.

## Structure

```
functions/
├── talk-stream/     # SSE streaming chat endpoint
├── welcome/         # Welcome message endpoint  
├── goodbye/         # Goodbye message endpoint
└── recquestions/    # Recommended questions endpoint

cdktf/              # Infrastructure as Code
├── main.ts         # Main deployment stack
└── components/     # Reusable components
```

## Setup

1. Copy `.env.template` to `.env` and configure:
   ```
   PROJECTID=your-gcp-project
   REGION=us-central1
   BILLING_ACCOUNT=your-billing-account
   ```

2. Install dependencies:
   ```bash
   cd cdktf
   npm install
   ```

3. Deploy:
   ```bash
   cdktf deploy
   ```

## API Endpoints

- `POST /talk` - Streaming chat response
- `POST /welcome` - Welcome message
- `POST /goodbye` - Goodbye message  
- `POST /recquestions` - Recommended questions

All endpoints return mocked responses for development.
# xiaoice_class_assistant

### Login your GCP account
```
gcloud auth application-default login
```

### Create API Key

```
gcloud auth login
gcloud config set project <project-id>
gcloud auth application-default set-quota-project <project-id>
```

## Admin Tools

Tools in `admin_tools/` help manage API keys and pre-generate configuration.

### Pre-generate Presentation Messages from PPTX

To cache presentation messages from PowerPoint slides:

```bash
cd admin_tools
./setup.sh  # Install dependencies
venv/bin/python preload_presentation_messages.py \
  --pptx /path/to/deck.pptx \
  --languages en,zh \
  --template "Welcome to {title}" \
  --slide 1
```

This updates `presentation_messages` in Firestore (`xiaoice_config/messages`), making `/api/welcome` responses faster by avoiding real-time generation.