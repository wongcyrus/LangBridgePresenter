#!/bin/bash

VENV_DIR=".venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# List of requirements files
REQUIREMENTS_FILES=(
    "backend/tests/requirements.txt"
    "backend/speaker_note_generator/requirements.txt"
    "backend/presentation-preloader/requirements.txt"
    "backend/admin_tools/requirements.txt"
    "backend/functions/config/requirements.txt"
    "backend/functions/goodbye/requirements.txt"
    "backend/functions/recquestions/requirements.txt"
    "backend/functions/speech/requirements.txt"
    "backend/functions/talk-stream/requirements.txt"
    "backend/functions/transcribe/requirements.txt"
    "backend/functions/welcome/requirements.txt"
    "client/python/requirements.txt"
)

FAILED_FILES=()

# Install requirements
for req_file in "${REQUIREMENTS_FILES[@]}"; do
    if [ -f "$req_file" ]; then
        echo "Installing dependencies from $req_file..."
        if ! pip install -r "$req_file"; then
            echo "Error installing dependencies from $req_file"
            FAILED_FILES+=("$req_file")
        fi
    else
        echo "Warning: $req_file not found, skipping."
    fi
done

if [ ${#FAILED_FILES[@]} -ne 0 ]; then
    echo "----------------------------------------"
    echo "Installation completed with errors."
    echo "The following files failed to install:"
    for file in "${FAILED_FILES[@]}"; do
        echo "  - $file"
    done
    exit 1
else
    echo "All requirements installed successfully."
fi
