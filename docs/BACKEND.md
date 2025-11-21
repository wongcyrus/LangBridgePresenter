# Backend Documentation

The backend is built on Google Cloud Platform (GCP) using a serverless architecture. It is deployed and managed using the Cloud Development Kit for Terraform (CDKTF).

## Infrastructure

The infrastructure code is located in `backend/cdktf/`.

- **Language**: TypeScript
- **Stack**: `XiaoiceApiStack`
- **Resources**:
    - **Cloud Functions (Gen 2)**: Python 3.11 runtimes.
    - **API Gateway**: Routes requests to functions.
    - **Firestore**: NoSQL database for state and cache.
    - **Cloud Storage**: Stores function source code.

## Cloud Functions

Located in `backend/functions/`.

### 1. Talk Stream (`talk-stream`)
- **Path**: `/api/talk`
- **Method**: POST
- **Purpose**: Handles user chat interactions.
- **Features**:
    - Streams responses using Server-Sent Events (SSE).
    - Maintains conversation history.
    - Uses a "Root Agent" configuration (`root_agent.yaml`) to define the AI persona.

### 2. Welcome (`welcome`)
- **Path**: `/api/welcome`
- **Method**: GET
- **Purpose**: Returns a greeting message when the application starts.
- **Logic**: Can be personalized based on the current context or time of day.

### 3. Goodbye (`goodbye`)
- **Path**: `/api/goodbye`
- **Method**: GET
- **Purpose**: Returns a farewell message.

### 4. Config (`config`)
- **Path**: `/api/config`
- **Method**: POST
- **Purpose**: Updates the current session context.
- **Usage**: Called by clients (VBA, Python Monitor) to push slide notes or screen text.

### 5. RecQuestions (`recquestions`)
- **Path**: `/api/recquestions`
- **Method**: GET
- **Purpose**: Generates recommended questions for the user to ask, based on the current context.

### 6. Speech (`speech`)
- **Path**: `/api/speech`
- **Method**: POST
- **Purpose**: Converts text to speech (TTS) if enabled.

## Data Model (Firestore)

The backend uses Firestore for persistence.

- **Collection**: `cache`
    - Stores pre-generated messages for slide content.
    - **Key Format**: `v1:{language}:{hash(content)}`
- **Collection**: `sessions` (implied)
    - Stores active conversation state.

## Deployment

To deploy the backend:

1. Navigate to `backend/cdktf`.
2. Install dependencies: `npm install`.
3. Synthesize Terraform config: `npx cdktf synth`.
4. Deploy: `npx cdktf deploy`.

See `backend/README.md` for detailed deployment prerequisites.
