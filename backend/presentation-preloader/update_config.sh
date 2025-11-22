#!/bin/bash

# Script to update config.py from cdktf outputs for the presentation preloader

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# CDKTF directory is one level up in 'backend/cdktf'
CDKTF_DIR="$SCRIPT_DIR/../cdktf"
CONFIG_FILE="$SCRIPT_DIR/config.py"

if [ ! -d "$CDKTF_DIR" ]; then
    echo "Error: CDKTF directory not found at $CDKTF_DIR"
    exit 1
fi

# Change to cdktf directory
cd "$CDKTF_DIR" || exit 1

echo "Fetching outputs from CDKTF..."

# Get outputs as JSON
# We use a simple grep to extract the JSON object if there is extra noise
OUTPUT_JSON=$(npx cdktf output --outputs-file-include-sensitive-outputs --outputs-file /dev/stdout 2>/dev/null | grep -A 1000 '{')

if [ -z "$OUTPUT_JSON" ]; then
    echo "Error: Could not retrieve cdktf outputs"
    exit 1
fi

# Extract variables
PROJECT_ID=$(echo "$OUTPUT_JSON" | grep -o '"project-id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')
API_SERVICE_NAME=$(echo "$OUTPUT_JSON" | grep -o '"api-service-name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')
SPEECH_FILE_BUCKET=$(echo "$OUTPUT_JSON" | grep -o '"speech-file-bucket"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')

if [ -z "$PROJECT_ID" ] || [ -z "$API_SERVICE_NAME" ]; then
    echo "Error: Could not parse project-id or api-service-name from outputs"
    exit 1
fi

echo "Retrieved configuration:"
echo "  project_id: $PROJECT_ID"
echo "  api: $API_SERVICE_NAME"
echo "  speech_file_bucket: $SPEECH_FILE_BUCKET"

# Update config.py
cat > "$CONFIG_FILE" << EOF
project_id="$PROJECT_ID"
api="$API_SERVICE_NAME"
speech_file_bucket="$SPEECH_FILE_BUCKET"
EOF

echo "Successfully updated $CONFIG_FILE"
