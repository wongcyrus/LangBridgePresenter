# Client Presentation Browser Design

## Overview
The LangBridge student client supports two modes of operation: **Live Mode** and **Browse Mode**. This allows users to seamlessly switch between following the live instructor and browsing previous slides or other presentation decks available in the course.

## Data Structure (Firestore)

The system uses a hierarchical structure in the **Client Firestore Project** (`langbridge-presenter-client`) under the `presentation_broadcast` collection.

```text
/presentation_broadcast/{courseId} (Root Document)
│
├── current_presentation_id: "cloudtech_en_with_visuals.pptm"  <-- Pointer to Live PPT
├── current_slide_id: "1"                                      <-- Pointer to Live Slide
├── latest_languages: { ... }                                  <-- Live Audio/Text Content
│
└── /presentations/{pptId} (Collection)                        <-- List of Available Decks
    │   (Parent document MUST exist for query discovery)
    ├── updated_at: timestamp
    │
    └── /slides/{slideId} (Subcollection)                      <-- Individual Slide Data
        ├── page_number: "1"
        ├── languages: {
        │   "en": { "text": "...", "audio_url": "...", "slide_link": "..." },
        │   "zh": { ... }
        │   }
        └── original_context: "..."
```

## Client Logic (`App.jsx`)

### 1. Mode Switching
*   **Live Mode (Default):** 
    *   The client subscribes to the root document (`/presentation_broadcast/{courseId}`).
    *   It automatically updates the viewed presentation and slide to match `current_presentation_id` and `current_slide_id`.
    *   The "LIVE" badge is green and active.
*   **Browse Mode:** 
    *   Activated automatically when the user manually selects a different presentation from the dropdown or navigates to a previous/next slide.
    *   The "LIVE" badge turns gray.
    *   Clicking the "LIVE" badge forces the client back into Live Mode and syncs with the broadcast.

### 2. Data Fetching
*   **Presentation List:** 
    *   Subscribes to `/presentation_broadcast/{courseId}/presentations` via `onSnapshot` to auto-populate the deck selector as new presentations are added.
*   **Slide Navigation:**
    *   **Live Mode:** Fetches content from `/presentations/{livePptId}/slides/{liveSlideId}`.
    *   **Browse Mode:** Fetches content from `/presentations/{selectedPptId}/slides/{selectedSlideId}`.
*   **Content Fallback:** 
    *   If visual content or text is missing in the specific slide registry document (e.g., due to replication latency), the client falls back to the `latest_languages` payload from the root document to ensure audio/text continuity.

### 3. UI Components
*   **Header:** Language selectors for View (Text) and Listen (Audio).
*   **Sub-Header:**
    *   **Presentation Dropdown:** Allows selection of distinct slide decks. Handles "No presentations found" state.
    *   **Navigation Controls:** Previous/Next buttons and specific Slide ID dropdown.
    *   **Live Badge:** Visual indicator and toggle button for Live Mode sync.
    *   **Autoplay:** Toggle for automatic audio playback when slides advance.
*   **Main Stage:** Displays the visual slide (image) and synchronized captions. Supports click-to-expand full-screen mode.

## Backend Integration
The Backend Cloud Function (`config`) acts as the broadcaster.

*   **Trigger:** Receives slide updates via HTTP POST from the seed script or Admin API.
*   **Actions:**
    1.  **Live Update:** Updates the **Root Document** with the latest live pointers (`current_presentation_id`, `current_slide_id`) and content.
    2.  **Parent Doc Creation:** Explicitly creates/updates the **Parent Presentation Document** (`/presentations/{pptId}`) to ensure it is not a "phantom document" and can be listed by clients.
    3.  **Registry Update:** Writes the full slide data to the **Slide Registry** (`/presentations/{pptId}/slides/{slideId}`).

## Security Rules
*   **Read:** Publicly readable (or authenticated student access) for `presentation_broadcast/{courseId}` and all its subcollections (`presentations`, `slides`).
*   **Write:** Restricted to the Backend API (via Admin SDK privileges).

## Implementation Notes & Troubleshooting

### 1. "Phantom Document" Issue
**Symptom:** The presentation dropdown is empty ("No presentations found"), but slide data exists in subcollections.
**Cause:** Firestore does not automatically create parent documents for nested collections. If `presentations/{pptId}` is not explicitly created, it remains a "phantom" document and does not appear in collection queries.
**Solution:** The Backend API must explicitly perform a `set()` on the parent presentation document (`presentations/{pptId}`) whenever it writes a slide. This ensures the document physically exists and is discoverable by client queries.

### 2. Presentation ID Normalization
**Symptom:** Mismatch between Live Mode pointer (e.g., `cloudtech.pptm`) and Browse Mode files (e.g., `cloudtech_en_with_visuals.pptm`).
**Cause:** Different inputs (Seed script vs. VBA client) may provide variations of the filename.
**Solution:** The Backend API normalizes incoming filenames (stripping language suffixes like `_en`, `_with_visuals`, etc.) and uses this normalized ID (`ppt_filename_norm`) as the canonical Firestore Document ID. This allows data from multiple sources or language runs to merge into a single, unified presentation entry (e.g., `cloudtech`).

### 3. Live vs. Browse Mode Sync
*   **Live Mode:** Driven by the `current_presentation_id` in the root document. If this ID points to a non-existent or phantom document, the view may be blank.
*   **Browse Mode:** Driven by the user's selection from the `presentations` collection.
*   **Recovery:** If Live Mode gets stuck on a bad ID, users can toggle Live Mode **OFF** (click the badge) and manually select a valid presentation from the dropdown to view content.
