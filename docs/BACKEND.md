# Backend Documentation

The backend is built on Google Cloud Platform (GCP) using a serverless architecture. It is deployed and managed using the Cloud Development Kit for Terraform (CDKTF).

## Infrastructure

The infrastructure code is located in `backend/cdktf/`.

- **Language**: TypeScript
- **Stack**: `LangBridgeApiStack`
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
    - Supports multiple presenters via comma-separated presenter IDs
    - Loads and merges presenter contexts (uses first presenter's course/presentation context)

### 2. Welcome (`welcome`)
- **Path**: `/api/welcome`
- **Method**: GET
- **Purpose**: Returns a greeting message when the application starts.
- **Logic**: Can be personalized based on the current context or time of day.
- **Features**:
    - Supports multiple presenters via comma-separated presenter IDs
    - Uses first presenter's language and current slide context for welcome message

### 3. Goodbye (`goodbye`)
- **Path**: `/api/goodbye`
- **Method**: GET
- **Purpose**: Returns a farewell message.

### 4. Config (`config`)
- **Path**: `/api/config`
- **Method**: POST
- **Purpose**: Updates the current session context.
- **Usage**: Called by clients (VBA, Python Monitor) to push slide notes or screen text.
- **Features**:
    - Supports multiple presenters via comma-separated presenter IDs in `userParams.presenterId`
    - Updates all specified presenters with current slide context
    - Broadcasts slide updates to client applications

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

- **Collection**: `langbridge_presentation_cache`
    - Stores pre-generated messages for slide content.
    - **Key Format**: `v1:{language}:{hash(content)}`
- **Collection**: `courses`
    - Stores course-specific configurations (languages, voices).
- **Collection**: `presenters`
    - Stores presenter-specific context and state.
    - **Fields**:
        - `id`: Presenter identifier
        - `name`: Presenter display name
        - `language`: Preferred language code
        - `background`: Presenter background/bio
        - `current_course_id`: Active course
        - `current_presentation_id`: Active presentation
        - `current_slide_id`: Current slide number
        - `current_slide_languages`: Current slide content in all languages
    - **Multiple Presenters**: The system supports comma-separated presenter IDs, allowing multiple AI agents to share the same presentation context.
- **Collection**: `sessions` (implied)
    - Stores active conversation state.

## Deployment

Full deployment instructions, including prerequisites and configuration, are available in **[Deployment Guide](DEPLOYMENT.md)**.

The backend is deployed as part of the unified system using the `./deploy.sh` script at the project root.
