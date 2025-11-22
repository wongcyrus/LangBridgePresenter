#!/bin/bash

# Script to build and deploy the web-student client to Firebase Hosting

# Exit on any error
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLIENT_DIR="$SCRIPT_DIR"

# Navigate to the client directory
cd "$CLIENT_DIR"

echo "🚀 Starting deployment for Web Student Client..."

# 1. Install Dependencies
echo "📦 Installing dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "   (Skipping install, node_modules exists)"
fi

# 2. Build the Project
echo "🔨 Building the project..."
npm run build

# 3. Deploy to Firebase
echo "🔥 Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo "✅ Deployment complete!"
