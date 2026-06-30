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
├── config/          # Config + presentation broadcast endpoint
├── voice-chat-access/# Voice chat access check for signed-in users
└── voice-chat-admin/# Admin usage dashboard + limit controls API

cdktf/              # Infrastructure as Code
├── main.ts         # Main deployment stack
└── components/     # Reusable components
```

## Setup

1. Create an environment file and configure it:
   ```
   cp cdktf/.env.template cdktf/.env
   # or for a separate dev stack:
   # cp cdktf/.env.dev.template cdktf/.env.dev
   ```
   ```
   PROJECTID=your-gcp-project
   REGION=us-central1
   BILLING_ACCOUNT=your-billing-account
   GOOGLE_OAUTH_CLIENT_ID=...apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=...
   ```

2. Install dependencies:
   ```bash
   cd cdktf
   npm install
   ```

3. Deploy (Phase 1):
   ```bash
   cd ..
   ./deploy.sh
   ```

   Deploy a separate dev environment file:
   ```bash
   ./deploy.sh --env-file backend/cdktf/.env.dev
   ```

Then complete:
- **Phase 2 (Auth):** initialize Authentication in Firebase console for the client project, then run `bootstrap_client_auth.py`.
- **Phase 3 (Content):** run `backend/seeds/seed_course_content.py` to load slide text/audio/visual data.

## API Endpoints

- `POST /api/talk` - Streaming chat response (SSE)
- `POST /api/welcome` - Welcome/presentation message
- `POST /api/goodbye` - Goodbye message
- `POST /api/recquestions` - Recommended questions
- `POST /api/speech` - Text-to-speech and voice URL
- `POST /api/config` - Update Firestore config and live presentation broadcast
- `GET /api/voice-chat-access` - Check if signed-in user is granted voice chat access
- `GET/POST /api/voice-chat-admin` - Admin usage and limit management

`talk-stream`, `welcome`, `goodbye`, `recquestions`, and `speech` use header-based request signature validation. `/api/config` is exposed through API Gateway key protection and updates Firestore-backed runtime state.

`/api/voice-chat-access` requires Firebase ID token authentication and returns whether the user is active in `voice_chat_users`.
`/api/voice-chat-admin` requires Firebase ID token authentication (`Authorization: Bearer <idToken>`) and admin access (custom claim, allowlist, or `admin_users` records).
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