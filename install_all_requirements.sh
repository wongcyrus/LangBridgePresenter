#!/bin/bash

VENV_DIR=".venv"
PYTHON_CMD="python3"

# Prefer Python 3.12
if [ -f "/usr/local/bin/python3.12" ]; then
    PYTHON_CMD="/usr/local/bin/python3.12"
elif command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
fi

echo "Using Python: $PYTHON_CMD"

# Check if venv exists and check its version
if [ -d "$VENV_DIR" ]; then
    VENV_VER=$("$VENV_DIR/bin/python" --version 2>&1 | awk '{print $2}')
    TARGET_VER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    
    if [ "$VENV_VER" != "$TARGET_VER" ]; then
        echo "Virtual environment version ($VENV_VER) does not match target version ($TARGET_VER)."
        echo "Recreating virtual environment..."
        rm -rf "$VENV_DIR"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR using $PYTHON_CMD..."
    $PYTHON_CMD -m venv "$VENV_DIR"
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
