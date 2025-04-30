# Whisper Subtitle Generator

<div align="center">
    <img src="whisper_subtitle_generator/resources/icons/app_icon.png" alt="Whisper Subtitle Generator Logo" width="200">
    <p>A powerful, user-friendly GUI application for generating subtitles from video files using OpenAI's Whisper.</p>
    <p>
        <a href="#features">Features</a> •
        <a href="#installation">Installation</a> •
        <a href="#usage">Usage</a> •
        <a href="#build">Build</a> •
        <a href="#contributing">Contributing</a> •
        <a href="#license">License</a>
    </p>
</div>

## Features

- **Easy-to-use GUI**: Simple interface for generating subtitles without command line knowledge
- **Batch Processing**: Process multiple videos in a folder at once
- **Smart Output**: Automatically save subtitles in the same folder as videos
- **Multiple Formats**: Export subtitles as SRT, VTT, JSON, or plain text
- **Translation Support**: Translate subtitles to multiple languages
- **Advanced Subtitle Control**: Customize line length and segment duration
- **High Accuracy**: Uses OpenAI's Whisper models for state-of-the-art speech recognition
- **GPU Acceleration**: Optional GPU support for faster processing
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system

### Install FFmpeg

#### Windows
1. Download from [FFmpeg official website](https://ffmpeg.org/download.html)
2. Add to your system PATH

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo dnf install ffmpeg  # Fedora
```

### Option 1: Install from PyPI

```bash
pip install whisper-subtitle-generator
```

### Option 2: Install from Source

```bash
git clone https://github.com/yourusername/whisper-subtitle-generator.git
cd whisper-subtitle-generator
pip install -e .
```

### Option 3: Download Pre-built Executable

Download the latest release from the [Releases](https://github.com/yourusername/whisper-subtitle-generator/releases) page.

## Usage

### Running the Application

```bash
# If installed from PyPI
whisper-subtitle-generator

# If installed from source
python -m whisper_subtitle_generator.gui
```

Or simply double-click the executable file if you downloaded the pre-built version.

### User Interface Overview

![Screenshot of Whisper Subtitle Generator](/screenshots/app_screenshot.png)

1. **Input Section**:
   - Choose between folder or file input
   - Select input path
   - Enable automatic output to input folder

2. **Model Settings**:
   - Select Whisper model (tiny, base, small, medium, large, large-v3)
   - Enable GPU acceleration

3. **Output Settings**:
   - Choose subtitle format (SRT, VTT, JSON, TXT)
   - Enable translation
   - Select target language

4. **Subtitle Options**:
   - Adjust maximum line length
   - Set maximum segment duration

5. **Action Controls**:
   - Start/stop processing
   - Monitor progress and current file

6. **Log Section**:
   - View detailed processing information

### Quick Start Guide

1. Select a folder with videos or a single video file
2. Choose your preferred model (start with "base" for balance of speed and accuracy)
3. Select output format (SRT is most compatible)
4. Click "Start Processing"
5. Subtitles will be saved alongside your video files

### Model Selection Guide

| Model | Size | Speed | Accuracy | Memory Required |
|-------|------|-------|----------|----------------|
| tiny  | 39M  | ~10x  | Low      | ~1GB           |
| base  | 74M  | ~7x   | Basic    | ~1GB           |
| small | 244M | ~4x   | Good     | ~2GB           |
| medium| 769M | ~2x   | Better   | ~5GB           |
| large | 1.5G | 1x    | Best     | ~10GB          |

## Build

To build standalone executables:

### Windows
```bash
cd scripts
build_windows.bat
```

### macOS
```bash
cd scripts
chmod +x build_macos.sh
./build_macos.sh
```

### Linux
```bash
cd scripts
chmod +x build_linux.sh
./build_linux.sh
```

The executables will be generated in the `dist` directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the project's coding style and includes appropriate tests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper) for the state-of-the-art speech recognition model
- [FFmpeg](https://ffmpeg.org/) for audio extraction capabilities
- All contributors who have helped to improve this project

---

If you find this tool useful, please consider giving it a star on GitHub and sharing it with others!

For questions, issues, or feature requests, please [open an issue](https://github.com/yourusername/whisper-subtitle-generator/issues).