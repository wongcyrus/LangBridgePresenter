#!/bin/bash
# Setup demo course with multiple languages

python manage_courses.py update --id demo --title "Demo Course" --langs en-US,zh-CN,yue-HK
