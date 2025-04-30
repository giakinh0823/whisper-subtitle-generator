#!/bin/bash
echo "Building Whisper Subtitle Generator for macOS..."

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r ../requirements.txt
pip install pyinstaller

# Create executable with PyInstaller
pyinstaller --name "Whisper Subtitle Generator" \
            --icon ../whisper_subtitle_generator/resources/icons/app_icon.icns \
            --windowed \
            --onefile \
            --add-data "../whisper_subtitle_generator/resources:resources" \
            ../whisper_subtitle_generator/gui.py

echo "Build complete! Application is in the 'dist' folder."