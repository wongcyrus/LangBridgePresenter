#!/bin/bash
# Update demo course configuration

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python manage_courses.py update --id demo --title "Demo Course" --langs en-US,zh-CN,yue-HK

echo ""
echo "Demo course updated successfully!"
