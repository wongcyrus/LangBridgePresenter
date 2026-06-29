#!/bin/bash

# Exit on any error
set -e

# --- Centralized Deployment Script ---
# This script orchestrates the full deployment of both backend infrastructure
# (via CDK Terrain / CDKTN) and the frontend web client (to Firebase Hosting).
#
# Prerequisites:
# 1. Ensure `backend/cdktf/.env` is properly configured with your project IDs and API keys.
# 2. Authenticate to gcloud and firebase CLI.
#
# Usage: ./deploy.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Verify backend/cdktf/.env exists
CDKTN_ENV_PATH="$SCRIPT_DIR/backend/cdktf/.env"
if [ ! -f "$CDKTN_ENV_PATH" ]; then
    echo "Error: backend/cdktf/.env not found. Please create and configure it based on .env.template."
    exit 1
fi

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
bash "$SCRIPT_DIR/backend/deploy.sh"

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



echo "
✅ Full deployment complete!"
