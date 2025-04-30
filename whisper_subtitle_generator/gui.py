#!/usr/bin/env python3
"""
Whisper Subtitle Generator GUI

A graphical user interface for generating subtitles from videos using OpenAI's Whisper.
"""
import os
import sys
import glob
import torch
import whisper
import threading
from datetime import datetime
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from whisper_subtitle_generator.utils import (
    format_timestamp, extract_audio, split_text_by_length, write_srt, write_vtt,
    check_ffmpeg_installed, log_with_timestamp, get_resource_path,
    save_settings, load_settings
)

# Default settings
DEFAULT_SETTINGS = {
    "input_type": "folder",
    "model_name": "base",
    "translate": False,
    "target_language": "vi",
    "subtitle_format": "srt",
    "max_line_length": 40,
    "max_segment_duration": 3.0,
    "use_gpu": torch.cuda.is_available(),
    "use_input_folder_as_output": True,
    "last_input_folder": "",
    "last_output_folder": ""
}

# Application settings file path
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".whisper_subtitle_generator_settings.json")


class WhisperGUI:
    """Main GUI class for the Whisper Subtitle Generator"""

    def __init__(self, root):
        """Initialize the Whisper GUI application"""
        self.root = root
        self.root.title("Whisper Subtitle Generator")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Load saved settings or use defaults
        self.settings = load_settings(SETTINGS_FILE)
        if not self.settings:
            self.settings = DEFAULT_SETTINGS

        # Set theme - modern style
        style = ttk.Style()
        if sys.platform.startswith('win'):
            style.theme_use('vista')
        elif sys.platform.startswith('darwin'):
            style.theme_use('aqua')
        else:
            style.theme_use('clam')

        # Variables
        self.input_type = tk.StringVar(value=self.settings.get("input_type", "folder"))
        self.input_path = tk.StringVar(value=self.settings.get("last_input_folder", ""))
        self.output_path = tk.StringVar(value=self.settings.get("last_output_folder", ""))
        self.use_input_folder_as_output = tk.BooleanVar(value=self.settings.get("use_input_folder_as_output", True))
        self.model_name = tk.StringVar(value=self.settings.get("model_name", "base"))
        self.translate = tk.BooleanVar(value=self.settings.get("translate", False))
        self.target_language = tk.StringVar(value=self.settings.get("target_language", "vi"))
        self.subtitle_format = tk.StringVar(value=self.settings.get("subtitle_format", "srt"))
        self.max_line_length = tk.IntVar(value=self.settings.get("max_line_length", 40))
        self.max_segment_duration = tk.DoubleVar(value=self.settings.get("max_segment_duration", 3.0))
        self.use_gpu = tk.BooleanVar(value=self.settings.get("use_gpu", torch.cuda.is_available()))
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

        # Initialize paths if empty
        if not self.output_path.get() and not self.use_input_folder_as_output.get():
            default_output = os.path.join(os.path.expanduser("~"), "Documents", "Subtitles")
            self.output_path.set(default_output)

        # Add event binding for input path changes
        self.input_path.trace_add("write", self.on_input_path_change)

        # Add binding for the use_input_folder checkbox
        self.use_input_folder_as_output.trace_add("write", self.on_use_input_folder_change)

        # Check for FFmpeg at startup
        if not check_ffmpeg_installed():
            messagebox.showwarning(
                "FFmpeg Not Found",
                "FFmpeg is required but was not found on your system.\n\n"
                "Please install FFmpeg and make sure it's in your PATH before using this application."
            )

        # Setup cleanup on exit
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Handle application closing"""
        if self.processing:
            if not messagebox.askyesno("Confirm Exit", "Processing is in progress. Are you sure you want to exit?"):
                return

        # Save settings
        self.save_current_settings()

        # Close the application
        self.root.destroy()

    def save_current_settings(self):
        """Save current settings to file"""
        settings = {
            "input_type": self.input_type.get(),
            "model_name": self.model_name.get(),
            "translate": self.translate.get(),
            "target_language": self.target_language.get(),
            "subtitle_format": self.subtitle_format.get(),
            "max_line_length": self.max_line_length.get(),
            "max_segment_duration": self.max_segment_duration.get(),
            "use_gpu": self.use_gpu.get(),
            "use_input_folder_as_output": self.use_input_folder_as_output.get(),
            "last_input_folder": self.input_path.get(),
            "last_output_folder": self.output_path.get()
        }
        save_settings(settings, SETTINGS_FILE)

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
        """Create the input section of the GUI"""
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
        """Create the model settings section of the GUI"""
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
        """Create the output settings section of the GUI"""
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
        """Create the subtitle options section of the GUI"""
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
        """Create the action buttons and progress section of the GUI"""
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
        """Create the log section of the GUI"""
        log_frame = ttk.LabelFrame(parent, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def browse_input(self):
        """Browse for input folder or file"""
        if self.input_type.get() == "folder":
            path = filedialog.askdirectory(title="Select Input Folder")
        else:
            path = filedialog.askopenfilename(title="Select Video File",
                                              filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.flv *.wmv")])
        if path:
            self.input_path.set(path)

    def browse_output(self):
        """Browse for output folder"""
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_path.set(path)

    def log(self, message):
        """Add a message to the log with timestamp"""
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def start_processing(self):
        """Start processing videos"""
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
        """Stop processing videos"""
        if self.processing:
            self.processing = False
            self.log("Processing stopped by user.")

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
        if not extract_audio(video_path, audio_path, logger=self.log):
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
                write_srt(result["segments"], subtitle_path,
                          self.max_line_length.get(), self.max_segment_duration.get())
            elif subtitle_format == "vtt":
                write_vtt(result["segments"], subtitle_path,
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
                    write_srt(translated_result["segments"], translation_path,
                              self.max_line_length.get(), self.max_segment_duration.get())
                elif subtitle_format == "vtt":
                    write_vtt(translated_result["segments"], translation_path,
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
            # Save settings after successful processing
            self.save_current_settings()


def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()