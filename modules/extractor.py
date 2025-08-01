"""
Audio extraction module using FFmpeg.
"""

import os
import time
import tempfile
import ffmpeg
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.ffmpeg_downloader import FFmpegManager

class AudioExtractor:
    """Extract audio from video files using FFmpeg."""
    
    def __init__(self):
        self.logger = get_logger()
        self.temp_files = []
        self.ffmpeg_manager = FFmpegManager()
    
    def extract(self, video_path: str, output_dir: Optional[str] = None, progress_callback=None) -> str:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to input video file
            output_dir: Directory for output file (default: temp directory)
            
        Returns:
            Path to extracted audio file
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Determine output path
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        
        video_name = Path(video_path).stem
        audio_path = os.path.join(output_dir, f"{video_name}_audio.wav")
        
        # Track temp file for cleanup
        self.temp_files.append(audio_path)
        
        try:
            # Ensure FFmpeg is available
            if progress_callback:
                progress_callback(0, "Checking FFmpeg...")
            
            if not self.ffmpeg_manager.ensure_ffmpeg(progress_callback):
                raise RuntimeError("FFmpeg is not available and could not be downloaded")
            
            if progress_callback:
                progress_callback(20, "Starting audio extraction...")
            
            self.logger.info(f"Extracting audio: {video_path} -> {audio_path}")
            
            # Get FFmpeg path
            ffmpeg_path = self.ffmpeg_manager.get_ffmpeg_path()
            
            # Use FFmpeg to extract audio
            # Convert to mono WAV at 16kHz for optimal speech recognition
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream.audio,
                audio_path,
                acodec='pcm_s16le',  # 16-bit PCM
                ac=1,                # Mono channel
                ar=16000,           # 16kHz sample rate
                y=None              # Overwrite output file
            )
            
            # Run the extraction with custom FFmpeg path
            if progress_callback:
                progress_callback(50, "Processing audio...")
            
            ffmpeg.run(stream, cmd=ffmpeg_path, capture_stdout=True, capture_stderr=True)
        
            if not os.path.exists(audio_path):
                raise RuntimeError("Audio extraction failed - output file not created")
            
            # Ensure file is fully written and accessible
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    file_size = os.path.getsize(audio_path)
                    if file_size > 0:
                        # Try to open the file to verify it's readable
                        with open(audio_path, 'rb') as f:
                            # Read a small chunk to ensure file is readable
                            f.read(1024)
                            break
                except Exception as e:
                    self.logger.warning(f"File not fully accessible yet: {str(e)}")
                
                # Wait before retrying
                time.sleep(1)
                retry_count += 1
            
            if retry_count == max_retries:
                self.logger.warning("File access verification timed out, but continuing anyway")
        
            self.logger.info(f"Audio extraction completed: {audio_path}")
            return audio_path
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error during audio extraction: {e.stderr.decode() if e.stderr else str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Audio extraction failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_audio_info(self, video_path: str) -> dict:
        """Get audio stream information from video file."""
        try:
            probe = ffmpeg.probe(video_path)
            audio_streams = [
                stream for stream in probe['streams'] 
                if stream['codec_type'] == 'audio'
            ]
            
            if not audio_streams:
                return {'has_audio': False}
            
            audio_stream = audio_streams[0]  # Use first audio stream
            
            info = {
                'has_audio': True,
                'codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'duration': float(audio_stream.get('duration', 0))
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get audio info: {str(e)}")
            return {'has_audio': False, 'error': str(e)}
    
    def validate_video_file(self, video_path: str) -> bool:
        """Validate if the file is a readable video with audio."""
        try:
            if not os.path.exists(video_path):
                return False
            
            probe = ffmpeg.probe(video_path)
            
            # Check for video stream
            has_video = any(
                stream['codec_type'] == 'video' 
                for stream in probe['streams']
            )
            
            # Check for audio stream
            has_audio = any(
                stream['codec_type'] == 'audio' 
                for stream in probe['streams']
            )
            
            return has_video and has_audio
            
        except Exception as e:
            self.logger.error(f"Video validation failed: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up temporary audio files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.debug(f"Removed temp file: {temp_file}")
            except Exception as e:
                self.logger.error(f"Failed to remove temp file {temp_file}: {str(e)}")

        self.temp_files.clear()

    def extract_segment(self, video_path: str, start: float, end: float, output_path: str) -> str:
        """Extract an audio segment from a video file.

        Args:
            video_path: Path to the source video file.
            start: Start time in seconds.
            end: End time in seconds.
            output_path: Path for the extracted audio file.

        Returns:
            Path to the extracted audio segment.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if end <= start:
            raise ValueError("End time must be greater than start time")

        # Ensure FFmpeg is available
        if not self.ffmpeg_manager.ensure_ffmpeg():
            raise RuntimeError("FFmpeg is not available and could not be downloaded")

        ffmpeg_path = self.ffmpeg_manager.get_ffmpeg_path()

        try:
            stream = ffmpeg.input(video_path, ss=start, to=end)
            stream = ffmpeg.output(
                stream.audio,
                output_path,
                acodec='pcm_s16le',
                ac=1,
                ar=16000,
                y=None
            )

            ffmpeg.run(stream, cmd=ffmpeg_path, capture_stdout=True, capture_stderr=True)

            if not os.path.exists(output_path):
                raise RuntimeError("Segment extraction failed - output file not created")

            return output_path

        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error during segment extraction: {e.stderr.decode() if e.stderr else str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            self.logger.error(f"Segment extraction failed: {str(e)}")
            raise
