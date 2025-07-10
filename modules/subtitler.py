"""
Subtitle generation module using pysubs2.
"""

import os
from pathlib import Path
from typing import List, Dict, Any

try:
    import pysubs2
    PYSUBS2_AVAILABLE = True
except ImportError:
    PYSUBS2_AVAILABLE = False

from utils.logger import get_logger

class SubtitleGenerator:
    """Generate subtitle files from transcription segments."""
    
    def __init__(self):
        self.logger = get_logger()
        
        if not PYSUBS2_AVAILABLE:
            raise ImportError("pysubs2 not available. Please install: pip install pysubs2")
    
    def generate(self, segments: List[Dict[str, Any]], video_path: str, format: str = "srt") -> str:
        """
        Generate subtitle file from transcription segments.
        
        Args:
            segments: List of transcription segments with start, end, text
            video_path: Original video file path (used for output naming)
            format: Subtitle format ('srt' or 'vtt')
            
        Returns:
            Path to generated subtitle file
        """
        if not segments:
            raise ValueError("No segments provided for subtitle generation")
        
        # Determine output path
        video_dir = Path(video_path).parent
        video_name = Path(video_path).stem
        subtitle_path = video_dir / f"{video_name}.{format.lower()}"
        
        try:
            self.logger.info(f"Generating {format.upper()} subtitles: {subtitle_path}")
            
            # Create subtitle file
            subs = pysubs2.SSAFile()
            
            for segment in segments:
                # Convert seconds to milliseconds for pysubs2
                start_ms = int(segment['start'] * 1000)
                end_ms = int(segment['end'] * 1000)
                text = segment['text']
                
                # Clean up text
                text = self.clean_text(text)
                
                if text:  # Only add non-empty text
                    # Create subtitle line
                    line = pysubs2.SSAEvent(
                        start=start_ms,
                        end=end_ms,
                        text=text
                    )
                    subs.append(line)
            
            # Save subtitle file
            if format.lower() == "srt":
                subs.save(str(subtitle_path), format_="srt")
            elif format.lower() == "vtt":
                subs.save(str(subtitle_path), format_="webvtt")
            else:
                raise ValueError(f"Unsupported subtitle format: {format}")
            
            self.logger.info(f"Subtitles generated: {subtitle_path} ({len(subs)} lines)")
            return str(subtitle_path)
            
        except Exception as e:
            error_msg = f"Subtitle generation failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def generate_both_formats(self, segments: List[Dict[str, Any]], video_path: str) -> Dict[str, str]:
        """Generate both SRT and VTT subtitle files."""
        results = {}
        
        try:
            results['srt'] = self.generate(segments, video_path, "srt")
            results['vtt'] = self.generate(segments, video_path, "vtt")
            return results
        except Exception as e:
            self.logger.error(f"Failed to generate subtitle formats: {str(e)}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean and format subtitle text."""
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove multiple spaces
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Handle common transcription artifacts
        text = text.replace(' .', '.')
        text = text.replace(' ,', ',')
        text = text.replace(' ?', '?')
        text = text.replace(' !', '!')
        
        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        
        return text
    
    def merge_short_segments(self, segments: List[Dict[str, Any]], min_duration: float = 1.0, max_chars: int = 100) -> List[Dict[str, Any]]:
        """
        Merge short segments to create better subtitle timing.
        
        Args:
            segments: Original segments
            min_duration: Minimum duration for a subtitle line
            max_chars: Maximum characters per subtitle line
            
        Returns:
            Merged segments
        """
        if not segments:
            return segments
        
        merged = []
        current_segment = None
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            text = segment['text']
            
            if current_segment is None:
                current_segment = segment.copy()
            elif (duration < min_duration and 
                  len(current_segment['text']) + len(text) <= max_chars and
                  segment['start'] - current_segment['end'] <= 1.0):  # Gap <= 1 second
                
                # Merge with current segment
                current_segment['end'] = segment['end']
                current_segment['text'] += " " + text
            else:
                # Start new segment
                merged.append(current_segment)
                current_segment = segment.copy()
        
        # Add last segment
        if current_segment:
            merged.append(current_segment)
        
        self.logger.info(f"Merged {len(segments)} segments into {len(merged)} subtitle lines")
        return merged
    
    def split_long_segments(self, segments: List[Dict[str, Any]], max_chars: int = 80, max_duration: float = 6.0) -> List[Dict[str, Any]]:
        """
        Split long segments into multiple subtitle lines.
        
        Args:
            segments: Original segments
            max_chars: Maximum characters per line
            max_duration: Maximum duration per line
            
        Returns:
            Split segments
        """
        split_segments = []
        
        for segment in segments:
            text = segment['text']
            duration = segment['end'] - segment['start']
            
            if len(text) <= max_chars and duration <= max_duration:
                split_segments.append(segment)
                continue
            
            # Split long text
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if len(test_line) <= max_chars:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Single word too long, force it
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Create segments for each line
            if lines:
                line_duration = duration / len(lines)
                for i, line in enumerate(lines):
                    start_time = segment['start'] + (i * line_duration)
                    end_time = start_time + line_duration
                    
                    split_segments.append({
                        'start': start_time,
                        'end': end_time,
                        'text': line
                    })
            else:
                split_segments.append(segment)
        
        return split_segments
    
    def optimize_subtitles(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize subtitle segments for better readability."""
        # First merge short segments
        optimized = self.merge_short_segments(segments)
        
        # Then split long segments
        optimized = self.split_long_segments(optimized)
        
        return optimized
