#!/bin/bash

# Exit on any error
set -e

# --- Centralized Deployment Script ---
# This script orchestrates the full deployment of both backend infrastructure
# (via CDK Terrain / CDKTN) and the frontend web client (to Firebase Hosting).
#
# Prerequisites:
# 1. Ensure your env file (default: `backend/cdktf/.env`) is configured with project IDs and keys.
# 2. Authenticate to gcloud and firebase CLI.
#
# Usage:
#   ./deploy.sh
#   ./deploy.sh --env-file backend/cdktf/.env.dev

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/backend/cdktf/.env"

if [ "${1:-}" = "--env-file" ]; then
    if [ -z "${2:-}" ]; then
        echo "Error: --env-file requires a path argument."
        exit 1
    fi
    ENV_FILE="$2"
fi

# Verify backend/cdktf/.env exists
CDKTN_ENV_PATH="$(realpath "$ENV_FILE")"
if [ ! -f "$CDKTN_ENV_PATH" ]; then
    echo "Error: env file not found at $CDKTN_ENV_PATH"
    exit 1
fi

export CDKTF_ENV_FILE="$CDKTN_ENV_PATH"
export CDKTF_ENV_PATH="$CDKTN_ENV_PATH"

# Source the .env file to make variables available for the rest of the script
# (especially for child scripts that might not explicitly load it)
set -a
# shellcheck disable=SC1090
. "$CDKTN_ENV_PATH"
set +a

echo "🚀 Starting full deployment..."

# Deploy Backend Infrastructure via CDK Terrain / CDKTN and sync config files
echo "
--- Deploying Backend Infrastructure ---"
# Capture absolute path for use after cd change
OUTPUT_FILE="$SCRIPT_DIR/backend/cdktf_outputs.json"

# 1. Run Deployment
bash "$SCRIPT_DIR/backend/deploy.sh" "$CDKTN_ENV_PATH"

# 2. Export Outputs for portability (this allows syncing on other machines)
echo "Exporting CDK Terrain outputs to $OUTPUT_FILE..."
cd "$SCRIPT_DIR/backend/cdktf"
# Use npx to run cdktn output and save to JSON
npx cdktn output --outputs-file-include-sensitive-outputs --outputs-file "$OUTPUT_FILE" --json

# 3. Run Sync Config (now uses the file if available)
echo "Running final configuration sync..."
cd "$SCRIPT_DIR"
SYNC_SCRIPT="$SCRIPT_DIR/backend/sync_config.py"
if [ -f "$SYNC_SCRIPT" ]; then
    python3 "$SYNC_SCRIPT"
else
    echo "Warning: sync_config.py not found at $SYNC_SCRIPT"
fi

echo "Bootstrapping client auth configuration..."
BOOTSTRAP_AUTH_SCRIPT="$SCRIPT_DIR/backend/admin_tools/bootstrap_client_auth.py"
if [ -f "$BOOTSTRAP_AUTH_SCRIPT" ]; then
    python3 "$BOOTSTRAP_AUTH_SCRIPT" --outputs-file "$OUTPUT_FILE"
else
    echo "Warning: bootstrap_client_auth.py not found at $BOOTSTRAP_AUTH_SCRIPT"
fi

echo "Deploying voice live proxy (Cloud Run)..."
VOICE_PROXY_DEPLOY_SCRIPT="$SCRIPT_DIR/backend/deploy_voice_proxy.sh"
if [ -f "$VOICE_PROXY_DEPLOY_SCRIPT" ]; then
    VOICE_PROXY_URL="$(bash "$VOICE_PROXY_DEPLOY_SCRIPT" | tail -n 1)"
    if [ -z "$VOICE_PROXY_URL" ]; then
        echo "Error: voice proxy deploy did not return a URL"
        exit 1
    fi
    VOICE_PROXY_WS_URL="${VOICE_PROXY_URL/https:/wss:}"
    CLIENT_ENV_FILE="$SCRIPT_DIR/client/web-student/.env"
    if [ -f "$CLIENT_ENV_FILE" ]; then
        grep -v '^VITE_VOICE_LIVE_PROXY_WS_URL=' "$CLIENT_ENV_FILE" > "$CLIENT_ENV_FILE.tmp" || true
        mv "$CLIENT_ENV_FILE.tmp" "$CLIENT_ENV_FILE"
        echo "VITE_VOICE_LIVE_PROXY_WS_URL=$VOICE_PROXY_WS_URL" >> "$CLIENT_ENV_FILE"
        grep -v '^VITE_GCP_PROJECT_ID=' "$CLIENT_ENV_FILE" > "$CLIENT_ENV_FILE.tmp" || true
        mv "$CLIENT_ENV_FILE.tmp" "$CLIENT_ENV_FILE"
        echo "VITE_GCP_PROJECT_ID=$PROJECTID" >> "$CLIENT_ENV_FILE"
    fi
else
    echo "Warning: voice proxy deploy script not found at $VOICE_PROXY_DEPLOY_SCRIPT"
fi

echo "
--- Deploying Web Client Hosting ---"
CLIENT_PROJECT_ID=$(jq -r '.cdktf["client-project-id"] // .cdktf["cdktf-langbridge-presenter-d2"]["client-project-id"] // .cdktf["cdktf-langbridge-presenter-dev"]["client-project-id"] // empty' "$OUTPUT_FILE")
if [ -z "$CLIENT_PROJECT_ID" ]; then
    echo "Error: client-project-id not found in $OUTPUT_FILE"
    exit 1
fi

cd "$SCRIPT_DIR/client/web-student"
npm install
npm run build
firebase deploy --only hosting --project "$CLIENT_PROJECT_ID"



echo "
✅ Full deployment complete!"
