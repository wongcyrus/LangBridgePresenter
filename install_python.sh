#!/bin/bash
set -e

PYTHON_VERSION="3.12.7"

if [ -f "/usr/local/bin/python3.12" ]; then
    echo "Python 3.12 is already installed in /usr/local/bin."
    /usr/local/bin/python3.12 --version
else
    echo "Updating package lists..."
    sudo apt-get update

    echo "Installing build dependencies..."
    sudo apt-get install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
    liblzma-dev python-openssl git

    echo "Downloading Python $PYTHON_VERSION..."
    cd /tmp
    wget https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz

    echo "Extracting..."
    tar -xf Python-$PYTHON_VERSION.tgz
    cd Python-$PYTHON_VERSION

    echo "Configuring..."
    ./configure --enable-optimizations

    echo "Building (this may take a few minutes)..."
    make -j $(nproc)

    echo "Installing..."
    sudo make altinstall

    echo "Cleaning up..."
    cd ..
    sudo rm -rf Python-$PYTHON_VERSION Python-$PYTHON_VERSION.tgz
    
    echo "Verifying installation..."
    python3.12 --version
fi

echo "Installing/Upgrading pip..."
if [ -f "/usr/local/bin/python3.12" ]; then
    PY_EXEC="/usr/local/bin/python3.12"
else
    PY_EXEC="python3.12"
fi

$PY_EXEC -m ensurepip --upgrade
$PY_EXEC -m pip install --upgrade pip

echo "Installing base packages (google-adk, fastapi, etc.)..."
$PY_EXEC -m pip install google-adk fastapi starlette uvicorn

echo "Python 3.12 installation complete."

