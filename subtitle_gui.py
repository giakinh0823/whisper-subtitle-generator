import os
import sys
import glob
import torch
import whisper
import subprocess
import re
import threading
import time
from pathlib import Path
import json
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper Subtitle Generator")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Set theme - modern style
        style = ttk.Style()
        if sys.platform.startswith('win'):
            style.theme_use('vista')
        elif sys.platform.startswith('darwin'):
            style.theme_use('aqua')
        else:
            style.theme_use('clam')

        # Variables
        self.input_type = tk.StringVar(value="folder")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.use_input_folder_as_output = tk.BooleanVar(value=True)
        self.model_name = tk.StringVar(value="base")
        self.translate = tk.BooleanVar(value=False)
        self.target_language = tk.StringVar(value="vi")
        self.subtitle_format = tk.StringVar(value="srt")
        self.max_line_length = tk.IntVar(value=40)
        self.max_segment_duration = tk.DoubleVar(value=3.0)
        self.use_gpu = tk.BooleanVar(value=torch.cuda.is_available())
        self.model = None
        self.processing = False
        self.current_file = tk.StringVar(value="")
        self.progress_value = tk.DoubleVar(value=0)

        # Main Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create the UI
        self.create_input_section(main_frame)
        self.create_model_section(main_frame)
        self.create_output_section(main_frame)
        self.create_options_section(main_frame)
        self.create_action_section(main_frame)
        self.create_log_section(main_frame)

        # Initialize paths
        default_output = os.path.join(os.path.expanduser("~"), "Documents", "Subtitles")
        self.output_path.set(default_output)

        # Add event binding for input path changes
        self.input_path.trace_add("write", self.on_input_path_change)

        # Add binding for the use_input_folder checkbox
        self.use_input_folder_as_output.trace_add("write", self.on_use_input_folder_change)

    def on_input_path_change(self, *args):
        """Update output path when input path changes, if the option is selected"""
        if self.use_input_folder_as_output.get() and self.input_path.get():
            if self.input_type.get() == "folder":
                self.output_path.set(self.input_path.get())
            else:
                # For file input, use the parent directory
                self.output_path.set(os.path.dirname(self.input_path.get()))

    def on_use_input_folder_change(self, *args):
        """Handle toggle of using input folder as output"""
        if self.use_input_folder_as_output.get() and self.input_path.get():
            if self.input_type.get() == "folder":
                self.output_path.set(self.input_path.get())
            else:
                # For file input, use the parent directory
                self.output_path.set(os.path.dirname(self.input_path.get()))
            # Disable the output path entry and browse button
            self.output_entry.config(state="disabled")
            self.output_browse_button.config(state="disabled")
        else:
            # Enable the output path entry and browse button
            self.output_entry.config(state="normal")
            self.output_browse_button.config(state="normal")

    def create_input_section(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        # Input type selection
        input_type_frame = ttk.Frame(input_frame)
        input_type_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

        ttk.Radiobutton(input_type_frame, text="Folder", variable=self.input_type, value="folder",
                        command=self.update_input_type).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(input_type_frame, text="File", variable=self.input_type, value="file",
                        command=self.update_input_type).pack(side=tk.LEFT)

        # Input path
        ttk.Label(input_frame, text="Input Path:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.input_path, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_input).grid(row=1, column=2, padx=5)

        # Output options
        ttk.Checkbutton(input_frame, text="Use input folder as output location",
                        variable=self.use_input_folder_as_output).grid(row=2, column=0, columnspan=3, sticky="w",
                                                                       pady=5)

        # Output path
        ttk.Label(input_frame, text="Output Path:").grid(row=3, column=0, sticky="w", pady=5)
        self.output_entry = ttk.Entry(input_frame, textvariable=self.output_path, width=50,
                                      state="disabled" if self.use_input_folder_as_output.get() else "normal")
        self.output_entry.grid(row=3, column=1, sticky="ew", padx=5)
        self.output_browse_button = ttk.Button(input_frame, text="Browse", command=self.browse_output,
                                               state="disabled" if self.use_input_folder_as_output.get() else "normal")
        self.output_browse_button.grid(row=3, column=2, padx=5)

        input_frame.columnconfigure(1, weight=1)

    def update_input_type(self):
        """Update UI based on input type selection"""
        if self.input_path.get():
            # Update output path based on new input type if use_input_folder is enabled
            self.on_input_path_change()

    def create_model_section(self, parent):
        model_frame = ttk.LabelFrame(parent, text="Model Settings", padding="10")
        model_frame.pack(fill=tk.X, padx=5, pady=5)

        # Model selection
        ttk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky="w", pady=5)
        models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        ttk.Combobox(model_frame, textvariable=self.model_name, values=models, state="readonly").grid(row=0, column=1,
                                                                                                      sticky="ew",
                                                                                                      padx=5)

        # GPU checkbox
        ttk.Checkbutton(model_frame, text="Use GPU (if available)", variable=self.use_gpu).grid(row=0, column=2, padx=5,
                                                                                                sticky="w")

    def create_output_section(self, parent):
        output_frame = ttk.LabelFrame(parent, text="Output Settings", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)

        # Format selection
        ttk.Label(output_frame, text="Format:").grid(row=0, column=0, sticky="w", pady=5)
        formats = ["srt", "vtt", "json", "txt"]
        ttk.Combobox(output_frame, textvariable=self.subtitle_format, values=formats, state="readonly").grid(row=0,
                                                                                                             column=1,
                                                                                                             sticky="ew",
                                                                                                             padx=5)

        # Translate checkbox
        ttk.Checkbutton(output_frame, text="Translate", variable=self.translate).grid(row=0, column=2, padx=5,
                                                                                      sticky="w")

        # Target language
        ttk.Label(output_frame, text="Target Language:").grid(row=1, column=0, sticky="w", pady=5)
        languages = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da",
                     "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi",
                     "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb",
                     "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn",
                     "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq",
                     "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi",
                     "yi", "yo", "zh"]
        ttk.Combobox(output_frame, textvariable=self.target_language, values=languages, state="readonly").grid(row=1,
                                                                                                               column=1,
                                                                                                               sticky="ew",
                                                                                                               padx=5)

    def create_options_section(self, parent):
        options_frame = ttk.LabelFrame(parent, text="Subtitle Options", padding="10")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # Max line length
        ttk.Label(options_frame, text="Max Line Length:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Spinbox(options_frame, from_=20, to=100, textvariable=self.max_line_length, width=5).grid(row=0, column=1,
                                                                                                      sticky="w",
                                                                                                      padx=5)

        # Max segment duration
        ttk.Label(options_frame, text="Max Segment Duration (sec):").grid(row=0, column=2, sticky="w", pady=5)
        ttk.Spinbox(options_frame, from_=1.0, to=10.0, increment=0.5, textvariable=self.max_segment_duration,
                    width=5).grid(row=0, column=3, sticky="w", padx=5)

    def create_action_section(self, parent):
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        # Progress info
        ttk.Label(action_frame, text="Current file:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(action_frame, textvariable=self.current_file, width=50).grid(row=0, column=1, sticky="w", padx=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(action_frame, orient="horizontal", mode="determinate",
                                            variable=self.progress_value)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(action_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Start Processing", command=self.start_processing, width=20).pack(side=tk.LEFT,
                                                                                                        padx=5)
        ttk.Button(button_frame, text="Stop", command=self.stop_processing, width=20).pack(side=tk.LEFT, padx=5)

        action_frame.columnconfigure(1, weight=1)

    def create_log_section(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def browse_input(self):
        if self.input_type.get() == "folder":
            path = filedialog.askdirectory(title="Select Input Folder")
        else:
            path = filedialog.askopenfilename(title="Select Video File",
                                              filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv")])
        if path:
            self.input_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_path.set(path)

    def log(self, message):
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def start_processing(self):
        if self.processing:
            messagebox.showwarning("Already Running", "Processing is already in progress.")
            return

        # Validate inputs
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input path.")
            return

        # Determine output path
        output_path = self.input_path.get() if self.use_input_folder_as_output.get() else self.output_path.get()
        if self.input_type.get() == "file" and self.use_input_folder_as_output.get():
            output_path = os.path.dirname(self.input_path.get())

        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Update output path display
        self.output_path.set(output_path)

        # Start processing in a separate thread
        self.processing = True
        self.progress_value.set(0)
        threading.Thread(target=self.process_videos, daemon=True).start()

    def stop_processing(self):
        if self.processing:
            self.processing = False
            self.log("Processing stopped by user.")

    def format_timestamp(self, seconds, always_include_hours=False):
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        ms = int(seconds * 1000)
        seconds, ms = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if always_include_hours or hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
        else:
            return f"{minutes:02d}:{seconds:02d},{ms:03d}"

    def write_srt(self, segments, file_path, max_line_length=None, max_segment_duration=None):
        """Write segments to a file in SRT format with line length and segment duration control"""
        with open(file_path, "w", encoding="utf-8") as f:
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

                        print(f"{current_index}", file=f)
                        print(f"{self.format_timestamp(chunk_start, always_include_hours=True)} --> "
                              f"{self.format_timestamp(chunk_end, always_include_hours=True)}", file=f)

                        # Apply max line length if needed
                        if max_line_length and len(chunk_text) > max_line_length:
                            lines = self.split_text_by_length(chunk_text, max_line_length)
                            print("\n".join(lines) + "\n", file=f)
                        else:
                            print(f"{chunk_text}\n", file=f)

                        current_index += 1
                else:
                    print(f"{current_index}", file=f)
                    print(f"{self.format_timestamp(start_time, always_include_hours=True)} --> "
                          f"{self.format_timestamp(end_time, always_include_hours=True)}", file=f)

                    # Apply max line length if needed
                    if max_line_length and len(text) > max_line_length:
                        lines = self.split_text_by_length(text, max_line_length)
                        print("\n".join(lines) + "\n", file=f)
                    else:
                        print(f"{text}\n", file=f)

                    current_index += 1

    def split_text_by_length(self, text, max_length):
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

    def write_vtt(self, segments, file_path, max_line_length=None, max_segment_duration=None):
        """Write segments to a file in VTT format with line length and segment duration control"""
        with open(file_path, "w", encoding="utf-8") as f:
            print("WEBVTT\n", file=f)
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

                        print(f"{self.format_timestamp(chunk_start, always_include_hours=True).replace(',', '.')} --> "
                              f"{self.format_timestamp(chunk_end, always_include_hours=True).replace(',', '.')}",
                              file=f)

                        # Apply max line length if needed
                        if max_line_length and len(chunk_text) > max_line_length:
                            lines = self.split_text_by_length(chunk_text, max_line_length)
                            print("\n".join(lines) + "\n", file=f)
                        else:
                            print(f"{chunk_text}\n", file=f)

                        current_index += 1
                else:
                    print(f"{self.format_timestamp(start_time, always_include_hours=True).replace(',', '.')} --> "
                          f"{self.format_timestamp(end_time, always_include_hours=True).replace(',', '.')}", file=f)

                    # Apply max line length if needed
                    if max_line_length and len(text) > max_line_length:
                        lines = self.split_text_by_length(text, max_line_length)
                        print("\n".join(lines) + "\n", file=f)
                    else:
                        print(f"{text}\n", file=f)

                    current_index += 1

    def extract_audio(self, video_path, audio_path):
        """Extract audio from video file using FFmpeg"""
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
            self.log(f"Error extracting audio from {video_path}: {e}")
            return False

    def process_video(self, video_path):
        """Process a single video file"""
        if not self.processing:
            return False

        # Determine the output folder
        if self.use_input_folder_as_output.get():
            if os.path.isdir(video_path):  # This should never happen, but just in case
                output_folder = video_path
            else:
                output_folder = os.path.dirname(video_path)
        else:
            output_folder = self.output_path.get()

        # Make sure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(output_folder, f"{base_name}.wav")

        # Update UI
        self.current_file.set(os.path.basename(video_path))
        self.log(f"Processing file: {os.path.basename(video_path)}")

        # Extract audio
        self.log(f"Extracting audio...")
        if not self.extract_audio(video_path, audio_path):
            self.log(f"Skipping {video_path} due to audio extraction error")
            return False

        # Transcribe
        self.log(f"Transcribing...")
        try:
            # Using OpenAI Whisper - always transcribe first
            result = self.model.transcribe(
                audio_path,
                task="transcribe",
                language="en",  # Source is English
                verbose=False
            )

            # If translation is requested, create a separate translation
            if self.translate.get():
                self.log(f"Translating to {self.target_language.get()}...")
                translated_result = self.model.transcribe(
                    audio_path,
                    task="translate",
                    language="en",  # Source is English
                    verbose=False
                )

            # Create subtitle file for original transcription
            subtitle_format = self.subtitle_format.get()
            subtitle_path = os.path.join(output_folder, f"{base_name}.{subtitle_format}")

            if subtitle_format == "srt":
                self.write_srt(result["segments"], subtitle_path,
                               self.max_line_length.get(), self.max_segment_duration.get())
            elif subtitle_format == "vtt":
                self.write_vtt(result["segments"], subtitle_path,
                               self.max_line_length.get(), self.max_segment_duration.get())
            elif subtitle_format == "json":
                with open(subtitle_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
            elif subtitle_format == "txt":
                with open(subtitle_path, "w", encoding="utf-8") as f:
                    f.write(result["text"])

            self.log(f"Created subtitle file: {os.path.basename(subtitle_path)}")

            # Create subtitle file for translation if requested
            if self.translate.get():
                target_lang = self.target_language.get()
                translation_path = os.path.join(output_folder,
                                                f"{base_name}.{target_lang}.{subtitle_format}")

                if subtitle_format == "srt":
                    self.write_srt(translated_result["segments"], translation_path,
                                   self.max_line_length.get(), self.max_segment_duration.get())
                elif subtitle_format == "vtt":
                    self.write_vtt(translated_result["segments"], translation_path,
                                   self.max_line_length.get(), self.max_segment_duration.get())
                elif subtitle_format == "json":
                    with open(translation_path, "w", encoding="utf-8") as f:
                        json.dump(translated_result, f, indent=4, ensure_ascii=False)
                elif subtitle_format == "txt":
                    with open(translation_path, "w", encoding="utf-8") as f:
                        f.write(translated_result["text"])

                self.log(f"Created translation file: {os.path.basename(translation_path)}")

            # Clean up temp audio file
            os.remove(audio_path)
            return True

        except Exception as e:
            self.log(f"Error processing {video_path}: {str(e)}")
            return False

    def process_videos(self):
        """Process all videos in the input path"""
        try:
            # Load the model
            self.log(f"Loading Whisper model: {self.model_name.get()}")
            device = "cuda" if self.use_gpu.get() and torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model(self.model_name.get(), device=device)
            self.log(f"Model loaded successfully on {device}")

            # Get video files
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']

            if self.input_type.get() == "folder":
                video_files = []
                for ext in video_extensions:
                    video_files.extend(glob.glob(os.path.join(self.input_path.get(), f"*{ext}")))
            else:
                video_files = [self.input_path.get()]

            if not video_files:
                self.log("No video files found!")
                self.processing = False
                return

            self.log(f"Found {len(video_files)} video file(s)")

            # Process each video
            success_count = 0
            for i, video_path in enumerate(video_files):
                if not self.processing:
                    break

                # Update progress
                self.progress_value.set((i / len(video_files)) * 100)

                if self.process_video(video_path):
                    success_count += 1

            # Update progress to 100%
            self.progress_value.set(100)

            self.log(f"Processing complete. Successfully processed {success_count} out of {len(video_files)} videos.")
            messagebox.showinfo("Complete", f"Successfully processed {success_count} out of {len(video_files)} videos.")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

        finally:
            self.processing = False
            self.current_file.set("")


if __name__ == "__main__":
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()