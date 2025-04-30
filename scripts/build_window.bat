@echo off
echo Building Whisper Subtitle Generator for Windows...

:: Create a virtual environment
python -m venv venv
call venv\Scripts\activate

:: Install requirements
pip install -r ..\requirements.txt
pip install pyinstaller

:: Create executable with PyInstaller
pyinstaller --name "Whisper Subtitle Generator" ^
            --icon ..\whisper_subtitle_generator\resources\icons\app_icon.ico ^
            --windowed ^
            --onefile ^
            --add-data "..\whisper_subtitle_generator\resources;resources" ^
            ..\whisper_subtitle_generator\gui.py

echo Build complete! Executable is in the "dist" folder.
pause