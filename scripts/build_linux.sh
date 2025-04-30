#!/bin/bash
echo "Building Whisper Subtitle Generator for Linux..."

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r ../requirements.txt
pip install pyinstaller

# Create executable with PyInstaller
pyinstaller --name "whisper-subtitle-generator" \
            --icon ../whisper_subtitle_generator/resources/icons/app_icon.png \
            --windowed \
            --onefile \
            --add-data "../whisper_subtitle_generator/resources:resources" \
            ../whisper_subtitle_generator/gui.py

echo "Build complete! Executable is in the 'dist' folder."