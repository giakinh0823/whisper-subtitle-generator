"""
Utility functions for the Whisper Subtitle Generator.
"""
import os
import re
import subprocess
import json
import glob
from datetime import datetime
import sys

def format_timestamp(seconds, always_include_hours=False):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)

    Args:
        seconds (float): Time in seconds
        always_include_hours (bool): Whether to always include hours

    Returns:
        str: Formatted timestamp
    """
    ms = int(seconds * 1000)
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if always_include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    else:
        return f"{minutes:02d}:{seconds:02d},{ms:03d}"


def extract_audio(video_path, audio_path, logger=None):
    """
    Extract audio from video file using FFmpeg

    Args:
        video_path (str): Path to video file
        audio_path (str): Path to save audio file
        logger (callable, optional): Function to log messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path, "-f", "wav", "-vn",
                "-ar", "16000", "-ac", "1", "-hide_banner",
                "-loglevel", "error", audio_path
            ],
            check=True
        )
        if logger:
            logger(f"Successfully extracted audio from {os.path.basename(video_path)}")
        return True
    except subprocess.CalledProcessError as e:
        if logger:
            logger(f"Error extracting audio from {video_path}: {e}")
        return False
    except FileNotFoundError:
        if logger:
            logger("FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
        return False


def split_text_by_length(text, max_length):
    """
    Split text into multiple lines with maximum length
    Try to split on sentence boundaries, then commas, then spaces

    Args:
        text (str): Text to split
        max_length (int): Maximum length of each line

    Returns:
        list: List of text lines
    """
    if len(text) <= max_length:
        return [text]

    lines = []

    # First try to split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_line = ""

    for sentence in sentences:
        if len(current_line) + len(sentence) + (1 if current_line else 0) <= max_length:
            if current_line:
                current_line += " " + sentence
            else:
                current_line = sentence
        else:
            if current_line:
                lines.append(current_line)

            # If the sentence itself is too long, split it further
            if len(sentence) > max_length:
                # Try to split by commas
                comma_parts = re.split(r'(?<=,)\s+', sentence)
                current_line = ""

                for part in comma_parts:
                    if len(current_line) + len(part) + (1 if current_line else 0) <= max_length:
                        if current_line:
                            current_line += " " + part
                        else:
                            current_line = part
                    else:
                        if current_line:
                            lines.append(current_line)

                        # If part is still too long, split by words
                        if len(part) > max_length:
                            words = part.split()
                            current_line = ""

                            for word in words:
                                if len(current_line) + len(word) + (1 if current_line else 0) <= max_length:
                                    if current_line:
                                        current_line += " " + word
                                    else:
                                        current_line = word
                                else:
                                    lines.append(current_line)
                                    current_line = word
                        else:
                            current_line = part
            else:
                current_line = sentence

    if current_line:
        lines.append(current_line)

    return lines


def write_srt(segments, file_path, max_line_length=None, max_segment_duration=None):
    """
    Write segments to a file in SRT format with line length and segment duration control

    Args:
        segments (list): List of segment dictionaries with start, end, and text keys
        file_path (str): Path to save SRT file
        max_line_length (int, optional): Maximum length of each subtitle line
        max_segment_duration (float, optional): Maximum duration of each subtitle segment in seconds
    """
    with open(file_path, "w", encoding="utf-8") as f:
        current_index = 1
        for segment in segments:
            # Check if we need to split segments due to length or duration
            text = segment['text'].strip()
            start_time = segment['start']
            end_time = segment['end']

            if max_segment_duration is not None and (end_time - start_time) > max_segment_duration:
                # Split large segments into smaller chunks
                words = text.split()
                num_words = len(words)
                chunk_size = max(1, num_words // int((end_time - start_time) / max_segment_duration + 0.5))

                for j in range(0, num_words, chunk_size):
                    chunk_words = words[j:j+chunk_size]
                    chunk_text = " ".join(chunk_words)

                    # Calculate proportional timing
                    portion = len(chunk_words) / num_words
                    chunk_duration = (end_time - start_time) * portion
                    chunk_start = start_time + (j / num_words) * (end_time - start_time)
                    chunk_end = min(end_time, chunk_start + chunk_duration)

                    print(f"{current_index}", file=f)
                    print(f"{format_timestamp(chunk_start, always_include_hours=True)} --> "
                          f"{format_timestamp(chunk_end, always_include_hours=True)}", file=f)

                    # Apply max line length if needed
                    if max_line_length and len(chunk_text) > max_line_length:
                        lines = split_text_by_length(chunk_text, max_line_length)
                        print("\n".join(lines) + "\n", file=f)
                    else:
                        print(f"{chunk_text}\n", file=f)

                    current_index += 1
            else:
                print(f"{current_index}", file=f)
                print(f"{format_timestamp(start_time, always_include_hours=True)} --> "
                      f"{format_timestamp(end_time, always_include_hours=True)}", file=f)

                # Apply max line length if needed
                if max_line_length and len(text) > max_line_length:
                    lines = split_text_by_length(text, max_line_length)
                    print("\n".join(lines) + "\n", file=f)
                else:
                    print(f"{text}\n", file=f)

                current_index += 1


def write_vtt(segments, file_path, max_line_length=None, max_segment_duration=None):
    """
    Write segments to a file in VTT format with line length and segment duration control

    Args:
        segments (list): List of segment dictionaries with start, end, and text keys
        file_path (str): Path to save VTT file
        max_line_length (int, optional): Maximum length of each subtitle line
        max_segment_duration (float, optional): Maximum duration of each subtitle segment in seconds
    """
    with open(file_path, "w", encoding="utf-8") as f:
        print("WEBVTT\n", file=f)

        for segment in segments:
            # Check if we need to split segments due to length or duration
            text = segment['text'].strip()
            start_time = segment['start']
            end_time = segment['end']

            if max_segment_duration is not None and (end_time - start_time) > max_segment_duration:
                # Split large segments into smaller chunks
                words = text.split()
                num_words = len(words)
                chunk_size = max(1, num_words // int((end_time - start_time) / max_segment_duration + 0.5))

                for j in range(0, num_words, chunk_size):
                    chunk_words = words[j:j+chunk_size]
                    chunk_text = " ".join(chunk_words)

                    # Calculate proportional timing
                    portion = len(chunk_words) / num_words
                    chunk_duration = (end_time - start_time) * portion
                    chunk_start = start_time + (j / num_words) * (end_time - start_time)
                    chunk_end = min(end_time, chunk_start + chunk_duration)

                    print(f"{format_timestamp(chunk_start, always_include_hours=True).replace(',', '.')} --> "
                          f"{format_timestamp(chunk_end, always_include_hours=True).replace(',', '.')}", file=f)

                    # Apply max line length if needed
                    if max_line_length and len(chunk_text) > max_line_length:
                        lines = split_text_by_length(chunk_text, max_line_length)
                        print("\n".join(lines) + "\n", file=f)
                    else:
                        print(f"{chunk_text}\n", file=f)
            else:
                print(f"{format_timestamp(start_time, always_include_hours=True).replace(',', '.')} --> "
                      f"{format_timestamp(end_time, always_include_hours=True).replace(',', '.')}", file=f)

                # Apply max line length if needed
                if max_line_length and len(text) > max_line_length:
                    lines = split_text_by_length(text, max_line_length)
                    print("\n".join(lines) + "\n", file=f)
                else:
                    print(f"{text}\n", file=f)


def get_supported_video_files(directory):
    """
    Get list of supported video files in a directory

    Args:
        directory (str): Directory to search for video files

    Returns:
        list: List of video file paths
    """
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
    video_files = []

    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(directory, f"*{ext}")))

    return video_files


def check_ffmpeg_installed():
    """
    Check if FFmpeg is installed and available

    Returns:
        bool: True if FFmpeg is installed, False otherwise
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def log_with_timestamp(message, log_file=None):
    """
    Log a message with timestamp

    Args:
        message (str): Message to log
        log_file (str, optional): Path to log file

    Returns:
        str: Formatted log message
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"

    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    return log_message


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller

    Args:
        relative_path (str): Path relative to resources directory

    Returns:
        str: Absolute path to resource
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, 'resources', relative_path)


def save_settings(settings, settings_file):
    """
    Save settings to a JSON file

    Args:
        settings (dict): Settings to save
        settings_file (str): Path to settings file
    """
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)


def load_settings(settings_file):
    """
    Load settings from a JSON file

    Args:
        settings_file (str): Path to settings file

    Returns:
        dict: Loaded settings
    """
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}