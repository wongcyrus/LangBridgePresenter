#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ID="${PROJECTID:-}"
REGION="${REGION:-us-east1}"
SERVICE_NAME="voice-live-proxy"
SERVICE_ACCOUNT="talk-streamtalkstream@${PROJECT_ID}.iam.gserviceaccount.com"
SOURCE_DIR="$SCRIPT_DIR/live-proxy"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECTID is not set in environment."
  exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: proxy source directory not found: $SOURCE_DIR"
  exit 1
fi

echo "Deploying Cloud Run voice proxy ($SERVICE_NAME) to project $PROJECT_ID..."
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --source "$SOURCE_DIR" \
  --allow-unauthenticated \
  --service-account "$SERVICE_ACCOUNT" \
  --timeout=3600 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-east1,CLIENT_FIREBASE_PROJECT_ID=${PROJECT_ID}-client,FIRESTORE_DATABASE=langbridge,VOICE_LIVE_MODEL=gemini-live-2.5-flash-native-audio"

URL="$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
if [ -z "$URL" ]; then
  echo "Error: failed to read Cloud Run URL for $SERVICE_NAME"
  exit 1
fi

echo "Voice proxy URL: $URL"
echo "$URL"
