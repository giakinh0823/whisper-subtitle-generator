#!/usr/bin/env python3
"""
Whisper Video Batch Processor

This script processes all video files in a specified folder, extracts subtitles using Whisper
from Hugging Face or OpenAI, and optionally translates them to a specified language.

Usage:
    python whisper_batch.py --input_folder /path/to/videos --output_folder /path/to/output
                           [--use_hf] [--model_path /path/to/model] [--model_name openai/whisper-base]
                           [--translate] [--target_language vi]
                           [--subtitle_format srt] [--max_line_length 40] [--max_segment_duration 3.0]

Requirements:
    - FFmpeg (for audio extraction)
    - Python 3.8+
    - For OpenAI version: openai-whisper
    - For Hugging Face version: transformers, datasets, accelerate
"""

import os
import argparse
import glob
import torch
import subprocess
import tqdm
import json
import re


def format_timestamp(seconds, always_include_hours=False):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
    """
    ms = int(seconds * 1000)
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if always_include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    else:
        return f"{minutes:02d}:{seconds:02d},{ms:03d}"


def write_srt(segments, file, max_line_length=None, max_segment_duration=None):
    """
    Write segments to a file in SRT format with line length and segment duration control
    """
    current_index = 1
    for i, segment in enumerate(segments):
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
                chunk_words = words[j:j + chunk_size]
                chunk_text = " ".join(chunk_words)

                # Calculate proportional timing
                portion = len(chunk_words) / num_words
                chunk_duration = (end_time - start_time) * portion
                chunk_start = start_time + (j / num_words) * (end_time - start_time)
                chunk_end = min(end_time, chunk_start + chunk_duration)

                print(f"{current_index}", file=file)
                print(f"{format_timestamp(chunk_start, always_include_hours=True)} --> "
                      f"{format_timestamp(chunk_end, always_include_hours=True)}", file=file)

                # Apply max line length if needed
                if max_line_length and len(chunk_text) > max_line_length:
                    lines = split_text_by_length(chunk_text, max_line_length)
                    print("\n".join(lines) + "\n", file=file)
                else:
                    print(f"{chunk_text}\n", file=file)

                current_index += 1
        else:
            print(f"{current_index}", file=file)
            print(f"{format_timestamp(start_time, always_include_hours=True)} --> "
                  f"{format_timestamp(end_time, always_include_hours=True)}", file=file)

            # Apply max line length if needed
            if max_line_length and len(text) > max_line_length:
                lines = split_text_by_length(text, max_line_length)
                print("\n".join(lines) + "\n", file=file)
            else:
                print(f"{text}\n", file=file)

            current_index += 1


def split_text_by_length(text, max_length):
    """
    Split text into multiple lines with maximum length
    Try to split on sentence boundaries, then commas, then spaces
    """
    if len(text) <= max_length:
        return [text]

    lines = []

    # First try to split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_line = ""

    for sentence in sentences:
        if len(current_line) + len(sentence) + 1 <= max_length:
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
                    if len(current_line) + len(part) + 1 <= max_length:
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
                                if len(current_line) + len(word) + 1 <= max_length:
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


def write_vtt(segments, file, max_line_length=None, max_segment_duration=None):
    """
    Write segments to a file in VTT format with line length and segment duration control
    """
    print("WEBVTT\n", file=file)
    current_index = 1

    for i, segment in enumerate(segments):
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
                chunk_words = words[j:j + chunk_size]
                chunk_text = " ".join(chunk_words)

                # Calculate proportional timing
                portion = len(chunk_words) / num_words
                chunk_duration = (end_time - start_time) * portion
                chunk_start = start_time + (j / num_words) * (end_time - start_time)
                chunk_end = min(end_time, chunk_start + chunk_duration)

                print(f"{format_timestamp(chunk_start, always_include_hours=True).replace(',', '.')} --> "
                      f"{format_timestamp(chunk_end, always_include_hours=True).replace(',', '.')}", file=file)

                # Apply max line length if needed
                if max_line_length and len(chunk_text) > max_line_length:
                    lines = split_text_by_length(chunk_text, max_line_length)
                    print("\n".join(lines) + "\n", file=file)
                else:
                    print(f"{chunk_text}\n", file=file)

                current_index += 1
        else:
            print(f"{format_timestamp(start_time, always_include_hours=True).replace(',', '.')} --> "
                  f"{format_timestamp(end_time, always_include_hours=True).replace(',', '.')}", file=file)

            # Apply max line length if needed
            if max_line_length and len(text) > max_line_length:
                lines = split_text_by_length(text, max_line_length)
                print("\n".join(lines) + "\n", file=file)
            else:
                print(f"{text}\n", file=file)

            current_index += 1


def extract_audio(video_path, audio_path):
    """
    Extract audio from video file using FFmpeg
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
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio from {video_path}: {e}")
        return False


def download_model_if_needed(model_name, model_path, use_hf=False):
    """
    Download the model if it's not already in the specified path
    """
    if use_hf:
        # For Hugging Face models
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        if model_path:
            os.makedirs(model_path, exist_ok=True)
            # If a path is provided, we'll use it to save and load the model
            try:
                print(f"Checking for HuggingFace model at {model_path}...")
                processor = WhisperProcessor.from_pretrained(model_path)
                model = WhisperForConditionalGeneration.from_pretrained(model_path)
                print(f"Loaded model from {model_path}")
            except Exception as e:
                print(f"Model not found at {model_path}, downloading from HuggingFace: {e}")
                print(f"Downloading model {model_name} from HuggingFace...")
                processor = WhisperProcessor.from_pretrained(model_name)
                model = WhisperForConditionalGeneration.from_pretrained(model_name)

                # Save the model to the specified path
                print(f"Saving model to {model_path}...")
                processor.save_pretrained(model_path)
                model.save_pretrained(model_path)
                print(f"Model saved to {model_path}")

            return {"model": model, "processor": processor}
        else:
            # If no path specified, load directly from HuggingFace
            print(f"Loading model {model_name} from HuggingFace...")
            processor = WhisperProcessor.from_pretrained(model_name)
            model = WhisperForConditionalGeneration.from_pretrained(model_name)
            return {"model": model, "processor": processor}
    else:
        # For OpenAI Whisper models
        import whisper
        if model_path:
            os.makedirs(model_path, exist_ok=True)
            # Check if model files already exist
            model_files = glob.glob(os.path.join(model_path, f"{model_name}*.pt"))
            if not model_files:
                print(f"Downloading OpenAI Whisper model {model_name} to {model_path}...")
                # OpenAI's whisper.load_model will download the model if needed
                whisper.load_model(model_name)
                print(f"Model {model_name} downloaded")
            return whisper.load_model(model_name)
        else:
            return whisper.load_model(model_name)


def process_video(video_path, output_folder, model_data, use_hf=False, translate=False, target_language="en",
                  subtitle_format="srt", max_line_length=None, max_segment_duration=None):
    """
    Process a single video file: extract audio, transcribe with Whisper, and save subtitles
    """
    global translated_result
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(output_folder, f"{base_name}.wav")

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Extract audio
    print(f"Extracting audio from {video_path}...")
    if not extract_audio(video_path, audio_path):
        print(f"Skipping {video_path} due to audio extraction error")
        return False

    # Transcribe
    print(f"Transcribing {video_path}...")
    try:
        if use_hf:
            # Using Hugging Face Transformers
            import librosa
            import numpy as np
            from transformers import pipeline

            # Create a transcription pipeline
            model = model_data["model"]
            processor = model_data["processor"]
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor
            )

            # Load audio file
            audio_array, sampling_rate = librosa.load(audio_path, sr=16000)

            # Transcribe with Hugging Face pipeline
            task = "transcribe"  # Always transcribe first
            generation_kwargs = {
                "task": task,
                "language": "en",  # Source is English
            }

            transcription = pipe(
                audio_array,
                chunk_length_s=30,
                batch_size=8,
                return_timestamps=True,
                generate_kwargs=generation_kwargs
            )

            # Format the result to match OpenAI Whisper output format
            result = {
                "text": transcription["text"],
                "segments": []
            }

            # Process chunks with timestamps
            for i, (chunk, timestamp) in enumerate(zip(
                    transcription["chunks"] if "chunks" in transcription else [transcription["text"]],
                    transcription["timestamp"] if "timestamp" in transcription else [
                        (0, len(audio_array) / sampling_rate)]
            )):
                result["segments"].append({
                    "id": i,
                    "start": timestamp[0],
                    "end": timestamp[1],
                    "text": chunk
                })

            # If translation is requested, create a separate translation
            if translate:
                print(f"Translating to {target_language}...")
                translation_kwargs = {
                    "task": "translate",
                    "language": "en",  # Source is English
                }

                # Set the target language
                if hasattr(processor, "get_decoder_prompt_ids"):
                    translation_kwargs["forced_decoder_ids"] = processor.get_decoder_prompt_ids(
                        language=target_language, task="translate"
                    )

                # Translate
                translation = pipe(
                    audio_array,
                    chunk_length_s=30,
                    batch_size=8,
                    return_timestamps=True,
                    generate_kwargs=translation_kwargs
                )

                # Format the translated result
                translated_result = {
                    "text": translation["text"],
                    "segments": []
                }

                # Process translation chunks with timestamps
                for i, (chunk, timestamp) in enumerate(zip(
                        translation["chunks"] if "chunks" in translation else [translation["text"]],
                        translation["timestamp"] if "timestamp" in translation else [
                            (0, len(audio_array) / sampling_rate)]
                )):
                    translated_result["segments"].append({
                        "id": i,
                        "start": timestamp[0],
                        "end": timestamp[1],
                        "text": chunk
                    })
        else:
            # Using OpenAI Whisper - always transcribe first
            result = model_data.transcribe(
                audio_path,
                task="transcribe",
                language="en",  # Source is English
                verbose=True
            )

            # If translation is requested, create a separate translation
            if translate:
                print(f"Translating to {target_language}...")
                translated_result = model_data.transcribe(
                    audio_path,
                    task="translate",
                    language="en",  # Source is English
                    verbose=True
                )

        # Create subtitle file for original transcription
        subtitle_path = os.path.join(output_folder, f"{base_name}.{subtitle_format}")
        with open(subtitle_path, "w", encoding="utf-8") as f:
            if subtitle_format == "srt":
                write_srt(result["segments"], f, max_line_length, max_segment_duration)
            elif subtitle_format == "vtt":
                write_vtt(result["segments"], f, max_line_length, max_segment_duration)
            elif subtitle_format == "json":
                json.dump(result, f, indent=4, ensure_ascii=False)
            elif subtitle_format == "txt":
                f.write(result["text"])

        print(f"Created subtitle file: {subtitle_path}")

        # Create subtitle file for translation if requested
        if translate:
            translation_path = os.path.join(output_folder, f"{base_name}.{target_language}.{subtitle_format}")
            with open(translation_path, "w", encoding="utf-8") as f:
                if subtitle_format == "srt":
                    write_srt(translated_result["segments"], f, max_line_length, max_segment_duration)
                elif subtitle_format == "vtt":
                    write_vtt(translated_result["segments"], f, max_line_length, max_segment_duration)
                elif subtitle_format == "json":
                    json.dump(translated_result, f, indent=4, ensure_ascii=False)
                elif subtitle_format == "txt":
                    f.write(translated_result["text"])

            print(f"Created translation file: {translation_path}")

        # Clean up temp audio file
        os.remove(audio_path)
        return True

    except Exception as e:
        print(f"Error processing {video_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Process videos with Whisper for subtitle generation")
    parser.add_argument("--input_folder", required=True, help="Folder containing video files")
    parser.add_argument("--output_folder", required=True, help="Folder to save subtitles")
    parser.add_argument("--use_hf", action="store_true", help="Use Hugging Face Transformers instead of OpenAI Whisper")
    parser.add_argument("--model_path", default=None, help="Path to store/load Whisper models")
    parser.add_argument("--model_name", default=None,
                        help="Model name or path. For OpenAI models: tiny, base, small, medium, large, turbo. For HF models: openai/whisper-tiny, etc.")
    parser.add_argument("--translate", action="store_true", help="Translate subtitles")
    parser.add_argument("--target_language", default="en", help="Target language for translation")
    parser.add_argument("--subtitle_format", default="srt",
                        choices=["srt", "vtt", "json", "txt"],
                        help="Subtitle output format")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu",
                        help="Device to run model on (cuda/cpu)")
    parser.add_argument("--max_line_length", type=int, default=40,
                        help="Maximum length of each subtitle line")
    parser.add_argument("--max_segment_duration", type=float, default=3.0,
                        help="Maximum duration of each subtitle segment in seconds")

    args = parser.parse_args()

    # Set default model name based on the source
    if args.model_name is None:
        if args.use_hf:
            args.model_name = "openai/whisper-base"
        else:
            args.model_name = "base"

    # Validate input folder
    if not os.path.isdir(args.input_folder):
        raise ValueError(f"Input folder does not exist: {args.input_folder}")

    # Create output folder if it doesn't exist
    os.makedirs(args.output_folder, exist_ok=True)

    # Download or load model
    print(
        f"{'Loading Hugging Face' if args.use_hf else 'Loading OpenAI'} Whisper model: {args.model_name} on {args.device}...")

    # Set torch device
    device = torch.device(args.device)

    # Download and load the model
    model_data = download_model_if_needed(args.model_name, args.model_path, use_hf=args.use_hf)

    if args.use_hf and isinstance(model_data, dict) and "model" in model_data:
        # For HF models, move to specified device
        model_data["model"] = model_data["model"].to(device)

    # Find all video files
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(args.input_folder, f"*{ext}")))

    if not video_files:
        print(f"No video files found in {args.input_folder}")
        return

    print(f"Found {len(video_files)} video files")

    # Process each video
    success_count = 0
    for video_path in tqdm.tqdm(video_files):
        if process_video(
                video_path,
                args.output_folder,
                model_data,
                use_hf=args.use_hf,
                translate=args.translate,
                target_language=args.target_language,
                subtitle_format=args.subtitle_format,
                max_line_length=args.max_line_length,
                max_segment_duration=args.max_segment_duration
        ):
            success_count += 1

    print(f"Processing complete. Successfully processed {success_count} out of {len(video_files)} videos.")


if __name__ == "__main__":
    main()

# example:
#  python subtitle_cli.py --input_folder '/path/to/videos' --output_folder ./subtitles --model_name large-v3 --translate --target_language vi

# example:
#  python subtitle_cli.py --input_folder '/Users/hagiakinh/Data/Study/DSA & AL/NeetCode - Algorithms & Data Structures for Beginners/01 ABOUT' --output_folder ./subtitles --model_name large-v3
# python subtitle_cli.py --input_folder '/Users/hagiakinh/Data/Study/DSA & AL/NeetCode - Algorithms & Data Structures for Beginners/01 ABOUT' --output_folder ./subtitles --model_name large-v3 --translate --target_language vi