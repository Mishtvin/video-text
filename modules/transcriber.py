"""
Speech recognition module using Whisper.
"""

import os
import time
from typing import List, Dict, Any, Callable, Optional

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from utils.logger import get_logger
from utils.ffmpeg_downloader import FFmpegManager

class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper."""
    
    def __init__(self, model_name: str = "base"):
        self.logger = get_logger()
        self.model_name = model_name
        self.model = None
        self.ffmpeg_manager = FFmpegManager()

        if not WHISPER_AVAILABLE:
            raise ImportError("Whisper not available. Please install: pip install openai-whisper")

        # Ensure FFmpeg is available and configure Whisper to use it
        try:
            if self.ffmpeg_manager.ensure_ffmpeg():
                ffmpeg_path = self.ffmpeg_manager.get_ffmpeg_path()
                # Set environment variable so Whisper uses the bundled FFmpeg
                os.environ["FFMPEG_BINARY"] = ffmpeg_path

                # Prepend FFmpeg directory to PATH so the 'ffmpeg' command is found
                ffmpeg_dir = os.path.dirname(ffmpeg_path)
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

                # Update whisper.audio if available (for newer library versions)
                try:
                    import whisper
                    whisper.audio.FFMPEG = ffmpeg_path
                except Exception:
                    pass

                self.logger.info("Using bundled FFmpeg")
            else:
                self.logger.warning("FFmpeg could not be ensured; Whisper may fail if FFmpeg is missing")
        except Exception as e:
            self.logger.warning(f"Failed to configure FFmpeg for Whisper: {str(e)}")
    
    def load_model(self):
        """Load the Whisper model."""
        if self.model is None:
            self.logger.info(f"Loading Whisper model: {self.model_name}")
            try:
                self.model = whisper.load_model(self.model_name)
                self.logger.info("Whisper model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load Whisper model: {str(e)}")
                raise
    
    def transcribe(self, audio_path: str, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Transcribe audio file to text with timestamps.
        
        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of segments with start, end, and text
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load model if not already loaded
        self.load_model()
        
        try:
            self.logger.info(f"Starting transcription: {audio_path}")
            start_time = time.time()
            
            # Progress callback for initial setup
            if progress_callback:
                progress_callback(0, "Loading audio...")
            
            # Transcribe with word-level timestamps
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )
            
            # Progress callback for processing
            if progress_callback:
                progress_callback(50, "Processing segments...")
            
            # Extract segments with timestamps
            segments = []
            for segment in result.get('segments', []):
                segment_data = {
                    'start': float(segment.get('start', 0)),
                    'end': float(segment.get('end', 0)),
                    'text': str(segment.get('text', '')).strip()
                }
                
                # Only add non-empty segments
                if segment_data['text']:
                    segments.append(segment_data)
            
            # Progress callback for completion
            if progress_callback:
                progress_callback(100, "Transcription completed")
            
            duration = time.time() - start_time
            self.logger.info(f"Transcription completed in {duration:.2f}s: {len(segments)} segments")
            
            return segments
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def transcribe_chunk(self, audio_path: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """Transcribe a specific chunk of audio."""
        self.load_model()
        
        try:
            # Load and transcribe the specific segment
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )
            
            # Filter segments within the time range
            segments = []
            for segment in result.get('segments', []):
                seg_start = float(segment.get('start', 0))
                seg_end = float(segment.get('end', 0))
                
                # Check if segment overlaps with requested time range
                if seg_start <= end_time and seg_end >= start_time:
                    # Adjust timestamps relative to chunk start
                    adjusted_start = max(0, seg_start - start_time)
                    adjusted_end = min(end_time - start_time, seg_end - start_time)
                    
                    segment_data = {
                        'start': adjusted_start,
                        'end': adjusted_end,
                        'text': str(segment.get('text', '')).strip()
                    }
                    
                    if segment_data['text']:
                        segments.append(segment_data)
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Chunk transcription failed: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en", 
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v1",
            "large-v2",
            "large"
        ]
    
    def estimate_processing_time(self, audio_duration_seconds: float) -> float:
        """Estimate processing time based on audio duration and model size."""
        # Rough estimates based on model size and typical performance
        time_ratios = {
            "tiny": 0.1,
            "tiny.en": 0.1,
            "base": 0.2,
            "base.en": 0.2,
            "small": 0.4,
            "small.en": 0.4,
            "medium": 0.8,
            "medium.en": 0.8,
            "large-v1": 1.5,
            "large-v2": 1.5,
            "large": 1.5
        }
        
        ratio = time_ratios.get(self.model_name, 0.5)
        return audio_duration_seconds * ratio
    
    def validate_audio_file(self, audio_path: str) -> bool:
        """Validate audio file for transcription."""
        try:
            if not os.path.exists(audio_path):
                return False
            
            # Check file size (should be > 0)
            if os.path.getsize(audio_path) == 0:
                return False
            
            # Basic format check (Whisper supports many formats)
            valid_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
            file_ext = os.path.splitext(audio_path)[1].lower()
            
            return file_ext in valid_extensions
            
        except Exception as e:
            self.logger.error(f"Audio validation failed: {str(e)}")
            return False
