# LangBridge Backend

GCP Cloud Functions implementation of LangBridge API endpoints using CDK Terrain (CDKTN) for deployment.

## Structure

```
functions/
├── talk-stream/     # SSE streaming chat endpoint
├── welcome/         # Welcome message endpoint  
├── goodbye/         # Goodbye message endpoint
├── recquestions/    # Recommended questions endpoint
├── speech/          # TTS endpoint
└── config/          # Config + presentation broadcast endpoint

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
   cdktn deploy
   ```

## API Endpoints

- `POST /api/talk` - Streaming chat response (SSE)
- `POST /api/welcome` - Welcome/presentation message
- `POST /api/goodbye` - Goodbye message
- `POST /api/recquestions` - Recommended questions
- `POST /api/speech` - Text-to-speech and voice URL
- `POST /api/config` - Update Firestore config and live presentation broadcast

`talk-stream`, `welcome`, `goodbye`, `recquestions`, and `speech` use header-based request signature validation. `/api/config` is exposed through API Gateway key protection and updates Firestore-backed runtime state.
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

To cache presentation messages from PowerPoint slides, use the `presentation-preloader` tool:

```bash
cd presentation-preloader
pip install -r requirements.txt
python main.py \
  --pptx /path/to/deck.pptx \
  --languages en,zh \
  --course-id "course_101"
```

This updates `presentation_messages` in Firestore (`langbridge_config/messages`), making `/api/welcome` responses faster by avoiding real-time generation.