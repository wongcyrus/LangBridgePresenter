#!/bin/bash

# Script to update admin_tools/config.py from cdktf outputs

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CDKTF_DIR="$SCRIPT_DIR/../cdktf"
CONFIG_FILE="$SCRIPT_DIR/config.py"

# Change to cdktf directory
cd "$CDKTF_DIR" || exit 1

# Get outputs as JSON
OUTPUT_JSON=$(npx cdktf output --outputs-file-include-sensitive-outputs --outputs-file /dev/stdout 2>/dev/null | grep -A 1000 '{')

if [ -z "$OUTPUT_JSON" ]; then
    echo "Error: Could not retrieve cdktf outputs"
    exit 1
fi

# Extract project-id and api-service-name using jq or grep/sed
PROJECT_ID=$(echo "$OUTPUT_JSON" | grep -o '"project-id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')
API_SERVICE_NAME=$(echo "$OUTPUT_JSON" | grep -o '"api-service-name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:.*"\([^"]*\)".*/\1/')

if [ -z "$PROJECT_ID" ] || [ -z "$API_SERVICE_NAME" ]; then
    echo "Error: Could not parse project-id or api-service-name from outputs"
    echo "Output JSON: $OUTPUT_JSON"
    exit 1
fi

echo "Retrieved from cdktf outputs:"
echo "  project_id: $PROJECT_ID"
echo "  api: $API_SERVICE_NAME"

# Update config.py
cat > "$CONFIG_FILE" << EOF
project_id="$PROJECT_ID"
api="$API_SERVICE_NAME"
EOF

echo "Successfully updated $CONFIG_FILE"
