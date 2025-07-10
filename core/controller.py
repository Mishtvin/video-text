"""
Main controller for coordinating video transcription operations.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from modules.extractor import AudioExtractor
from modules.transcriber import WhisperTranscriber
from modules.subtitler import SubtitleGenerator
from modules.indexer import TranscriptionIndexer
from utils.logger import get_logger

class TranscriptionController:
    """Main controller for video transcription and search operations."""
    
    def __init__(self):
        self.logger = get_logger()
        self.extractor = AudioExtractor()
        self.transcriber = WhisperTranscriber()
        self.subtitler = SubtitleGenerator()
        self.indexer = TranscriptionIndexer()
        
        # Cache for processed videos
        self.video_cache = {}
        
    def extract_audio(self, video_path: str, progress_callback=None) -> str:
        """Extract audio from video file."""
        self.logger.info(f"Extracting audio from: {video_path}")
        
        try:
            audio_path = self.extractor.extract(video_path, progress_callback=progress_callback)
            self.logger.info(f"Audio extracted to: {audio_path}")
            return audio_path
        except Exception as e:
            self.logger.error(f"Audio extraction failed: {str(e)}")
            raise
    
    def transcribe_audio(self, audio_path: str, progress_callback=None) -> List[Dict[str, Any]]:
        """Transcribe audio to text with timestamps."""
        self.logger.info(f"Transcribing audio: {audio_path}")
        
        try:
            segments = self.transcriber.transcribe(audio_path, progress_callback)
            self.logger.info(f"Transcription completed: {len(segments)} segments")
            return segments
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            raise
    
    def generate_subtitles(self, segments: List[Dict[str, Any]], video_path: str) -> str:
        """Generate subtitle files from transcription segments."""
        self.logger.info(f"Generating subtitles for: {video_path}")
        
        try:
            subtitle_path = self.subtitler.generate(segments, video_path)
            self.logger.info(f"Subtitles generated: {subtitle_path}")
            return subtitle_path
        except Exception as e:
            self.logger.error(f"Subtitle generation failed: {str(e)}")
            raise
    
    def index_segments(self, segments: List[Dict[str, Any]], video_path: str):
        """Index transcription segments for search."""
        self.logger.info(f"Indexing segments for: {video_path}")
        
        try:
            self.indexer.index_video(video_path, segments)
            
            # Cache the segments
            self.video_cache[video_path] = segments
            
            self.logger.info(f"Indexing completed: {len(segments)} segments")
        except Exception as e:
            self.logger.error(f"Indexing failed: {str(e)}")
            raise
    
    def search_transcription(self, video_path: str, query: str) -> List[Dict[str, Any]]:
        """Search through transcription text."""
        self.logger.info(f"Searching for '{query}' in: {video_path}")
        
        try:
            results = self.indexer.search(video_path, query)
            self.logger.info(f"Search completed: {len(results)} results found")
            return results
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise
    
    def get_transcription_segments(self, video_path: str) -> List[Dict[str, Any]]:
        """Get cached transcription segments for a video."""
        if video_path in self.video_cache:
            return self.video_cache[video_path]
        
        # Try to load from database
        try:
            segments = self.indexer.get_all_segments(video_path)
            if segments:
                self.video_cache[video_path] = segments
                return segments
        except Exception as e:
            self.logger.error(f"Failed to load segments from database: {str(e)}")
        
        return []
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get information about a processed video."""
        try:
            info = {
                'path': video_path,
                'name': Path(video_path).name,
                'size': os.path.getsize(video_path) if os.path.exists(video_path) else 0,
                'transcribed': video_path in self.video_cache or self.indexer.is_video_indexed(video_path),
                'segments_count': len(self.get_transcription_segments(video_path))
            }
            return info
        except Exception as e:
            self.logger.error(f"Failed to get video info: {str(e)}")
            return {}
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        try:
            self.extractor.cleanup()
            self.logger.info("Temporary files cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
