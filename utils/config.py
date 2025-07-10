"""
Configuration and utility functions for the application.
"""

import os
import sys
from pathlib import Path

def get_app_data_dir() -> str:
    """Get the application data directory based on the operating system."""
    if sys.platform == "win32":
        # Windows: use AppData/Roaming
        app_data = os.getenv("APPDATA")
        if app_data:
            return os.path.join(app_data, "VideoTranscriber")
        else:
            return os.path.join(Path.home(), "AppData", "Roaming", "VideoTranscriber")
    
    elif sys.platform == "darwin":
        # macOS: use ~/Library/Application Support
        return os.path.join(Path.home(), "Library", "Application Support", "VideoTranscriber")
    
    else:
        # Linux and others: use ~/.local/share
        return os.path.join(Path.home(), ".local", "share", "VideoTranscriber")

def get_temp_dir() -> str:
    """Get temporary directory for the application."""
    import tempfile
    return tempfile.gettempdir()

def ensure_directory(dir_path: str) -> str:
    """Ensure directory exists, create if it doesn't."""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def get_supported_video_formats() -> list:
    """Get list of supported video file formats."""
    return [
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', 
        '.flv', '.webm', '.m4v', '.3gp', '.ogv'
    ]

def get_supported_audio_formats() -> list:
    """Get list of supported audio file formats."""
    return [
        '.wav', '.mp3', '.m4a', '.flac', '.ogg', 
        '.aac', '.wma', '.opus'
    ]

def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format."""
    ext = Path(file_path).suffix.lower()
    return ext in get_supported_video_formats()

def is_audio_file(file_path: str) -> bool:
    """Check if file is a supported audio format."""
    ext = Path(file_path).suffix.lower()
    return ext in get_supported_audio_formats()

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def format_duration(seconds: float) -> str:
    """Format duration in HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

# Application constants
APP_NAME = "Video Transcriber"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Offline Video Transcription and Search"

# Default configuration values
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_AUDIO_SAMPLE_RATE = 16000
DEFAULT_AUDIO_CHANNELS = 1

# File patterns for dialogs
VIDEO_FILE_FILTER = "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.3gp *.ogv);;All Files (*)"
AUDIO_FILE_FILTER = "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma *.opus);;All Files (*)"
SUBTITLE_FILE_FILTER = "Subtitle Files (*.srt *.vtt);;All Files (*)"
