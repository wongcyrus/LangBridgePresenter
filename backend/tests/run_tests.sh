#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/.."
SYNC_SCRIPT="$BACKEND_DIR/sync_config.py"
VENV_DIR="$SCRIPT_DIR/venv"

echo "========================================="
echo "LangBridge Test Runner"
echo "========================================="

# 1. Sync Configuration (generates .env.test and other config files)
echo ""
echo "[1/4] Syncing configuration..."
if [ -f "$SYNC_SCRIPT" ]; then
    python3 "$SYNC_SCRIPT"
    echo "✓ Configuration synced"
else
    echo "⚠ Warning: sync_config.py not found at $SYNC_SCRIPT"
    echo "  Continuing with existing configuration..."
fi

# 2. Setup Virtual Environment
cd "$SCRIPT_DIR" || exit 1
echo ""
echo "[2/4] Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating new virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "✗ Failed to activate virtual environment"
    exit 1
fi

# 3. Install Dependencies
echo ""
echo "[3/4] Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt
echo "✓ Dependencies installed"

# 4. Verify .env.test exists
echo ""
if [ ! -f ".env.test" ]; then
    echo "⚠ Warning: .env.test not found!"
    echo "  Please create .env.test with:"
    echo "    API_URL=<your-api-url>"
    echo "    XIAOICE_CHAT_SECRET_KEY=<your-secret-key>"
    echo "    XIAOICE_CHAT_ACCESS_KEY=<your-access-key>"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ .env.test found"
fi

# 5. Run Tests
echo ""
echo "[4/4] Running tests..."
echo "========================================="
pytest -v --tb=short "$@"

echo ""
echo "========================================="
echo "Test run complete!"
echo "========================================="
