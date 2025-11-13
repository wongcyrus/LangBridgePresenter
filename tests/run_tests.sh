#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CDKTF_DIR="$SCRIPT_DIR/../cdktf"
TESTS_DIR="$SCRIPT_DIR"
VENV_DIR="$TESTS_DIR/venv"

cd "$CDKTF_DIR" || exit 1

# Get terraform outputs
OUTPUT_JSON=$(npx cdktf output --outputs-file-include-sensitive-outputs --outputs-file /dev/stdout 2>/dev/null | grep -A 1000 '{')

if [ -z "$OUTPUT_JSON" ]; then
    echo "Error: Could not retrieve cdktf outputs"
    exit 1
fi

PROJECT_ID=$(echo "$OUTPUT_JSON" | grep -o '"project-id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')
API_URL=$(echo "$OUTPUT_JSON" | grep -o '"api-url"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')

if [ -z "$PROJECT_ID" ] || [ -z "$API_URL" ]; then
    echo "Error: Could not parse outputs"
    exit 1
fi

echo "Using API URL: https://$API_URL"

cd "$TESTS_DIR" || exit 1

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Setup virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Set environment variables and run tests
export API_URL="https://$API_URL"
export ChatSecretKey="${ChatSecretKey:-test_secret_key}"
export ChatAccessKey="${ChatAccessKey:-test_access_key}"

python test_functions.py "$@"
