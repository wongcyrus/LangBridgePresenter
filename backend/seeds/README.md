# Backend Seeds

This directory contains scripts to seed the backend with demo data.

## `seed_demo_class.py`

This script does two things:
1.  **Creates a Demo Course** (`physics-101-demo`) in Firestore directly (using Admin privileges).
2.  **Simulates a Live Presentation** by sending HTTP requests to the Backend API, just like the VBA client would. This triggers the generation of AI messages and audio, and populates the `presentation_broadcast` collection.

### Prerequisites

1.  You must have `requests` installed:
    ```bash
    pip install requests
    ```
2.  You must have Google Cloud credentials configured if running locally (for step 1).
3.  You need the URL of your deployed (or local) `config` Cloud Function.

### Usage

```bash
# Navigate to backend
cd backend

# Run the seeder
python seeds/seed_demo_class.py \
  --api-url "https://<YOUR_GATEWAY_OR_FUNCTION_URL>/config" \
  --api-key "<YOUR_API_KEY>"
```

**Arguments:**
*   `--api-url`: The full URL to the `config` function endpoint.
*   `--api-key`: (Optional) The API Key if required by your Gateway.
*   `--skip-create`: (Optional) If you've already created the course and just want to re-run the simulation.

### What happens?

1.  The script creates `courses/physics-101-demo` in Firestore with languages `en-US`, `zh-CN`, and `yue-HK`.
2.  It then loops through 6 slides of a mock Physics lecture.
3.  For each slide, it sends a POST request to the API with the speaker notes, filename, and slide number.
4.  The backend processes this, generates translations/summaries, synthesizes speech, and broadcasts the update.
5.  If you have the Web Student Client open and connected to `physics-101-demo`, you will see the updates appear live!
