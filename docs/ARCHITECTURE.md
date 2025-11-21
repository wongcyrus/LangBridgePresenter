# System Architecture

The Xiaoice Class Assistant is a comprehensive system designed to enhance presentations and classroom interactions using AI. It consists of a serverless backend on Google Cloud Platform and client-side applications for real-time context monitoring.

## High-Level Overview

The system follows a client-server architecture where client applications (PowerPoint, Desktop Monitor) send context (slide notes, screen content) to a backend API. The backend processes this context using Large Language Models (Gemini) to generate relevant speech or chat responses.

```mermaid
graph TD
    User[User/Presenter] -->|Uses| PPT[PowerPoint (VBA)]
    User -->|Uses| Monitor[Window Monitor (Python)]
    User -->|Interacts| Chat[Chat Interface]

    subgraph "Client Side"
        PPT -->|Sends Slide Notes| API[API Gateway]
        Monitor -->|Sends OCR Text| API
    end

    subgraph "Backend (GCP)"
        API -->|Routes| CF[Cloud Functions]
        
        CF -->|Read/Write| Firestore[(Firestore DB)]
        CF -->|Read/Write| Storage[(Cloud Storage)]
        
        subgraph "Cloud Functions"
            Talk[Talk Stream]
            Welcome[Welcome]
            Goodbye[Goodbye]
            Config[Config/Cache]
        end
        
        Config -->|Pre-generated| Firestore
        Talk -->|Stream Response| Chat
    end

    subgraph "AI Services"
        CF -->|Inference| Gemini[Gemini 1.5 Flash]
    end
```

## Components

### 1. Backend
- **Infrastructure**: Managed via CDK for Terraform (CDKTF).
- **Compute**: Google Cloud Functions (Gen 2) for serverless execution.
- **API**: Google API Gateway for routing and security (API Keys).
- **Database**: Firestore for storing configuration, session state, and cached messages.
- **Storage**: Cloud Storage for artifacts.
- **AI**: Integration with Gemini 1.5 Flash for text generation.

### 2. Clients
- **VBA Client (PowerPoint)**: 
    - Embeds into PowerPoint presentations.
    - Detects slide changes.
    - Sends speaker notes to the backend to prime the AI context.
    - Supports content-based caching to handle slide reordering.
- **Python Client (Window Monitor)**:
    - Runs on the presenter's machine.
    - Periodically captures the screen or specific windows.
    - Uses OCR (Tesseract) to extract text.
    - Sends text changes to the backend to keep the AI aware of the visual context.

### 3. Admin Tools
- **Preloader**: Scripts to pre-generate AI responses for presentation slides.
- **Key Management**: Tools to generate and revoke API keys.

## Data Flow

1. **Context Update**:
   - **PowerPoint**: When a slide changes, the VBA macro extracts speaker notes and sends them to the `/config` endpoint.
   - **Monitor**: When screen text changes, the Python monitor sends the new text to the backend.
   
2. **Caching (Optimization)**:
   - The backend checks if a response for the specific content (hash of notes/text) already exists in Firestore.
   - If yes, it returns the cached response (low latency).
   - If no, it triggers the AI to generate a new response.

3. **Interaction**:
   - Users ask questions via the chat interface.
   - The `talk-stream` function retrieves the current context (set by clients).
   - It appends the user question and streams the AI's response back.

## Security
- **API Keys**: All client requests must be authenticated with a valid API key.
- **Firestore Rules**: Data access is controlled via security rules.
