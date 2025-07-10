"""
Speech recognition module using Whisper.
"""

import os
import time
import ctypes
import numpy as np
from typing import List, Dict, Any, Callable, Optional

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from utils.logger import get_logger
from utils.ffmpeg_downloader import FFmpegManager


def get_long_path(short_path):
    """Convert Windows 8.3 short path to long path"""
    if not os.path.exists(short_path):
        return short_path
    
    try:
        buffer_size = 260  # MAX_PATH
        buffer = ctypes.create_unicode_buffer(buffer_size)
        get_long_path_name = ctypes.windll.kernel32.GetLongPathNameW
        result = get_long_path_name(short_path, buffer, buffer_size)
        if result == 0:
            return short_path  # Return original if conversion fails
        return buffer.value
    except Exception:
        return short_path  # Return original if any error occurs

class WhisperTranscriber:
    """Class for transcribing audio files using OpenAI's Whisper."""
    
    def __init__(self, model_name="base", ffmpeg_manager=None, language=None):
        """Initialize the transcriber.
        
        Args:
            model_name: Name of the Whisper model to use ("tiny", "base", "small", "medium", "large").
            ffmpeg_manager: FFmpegManager instance for handling FFmpeg paths.
            language: Language code to use for transcription (e.g., "uk" for Ukrainian).
                     If None, language will be auto-detected.
        """
        self.model_name = model_name
        self.model = None
        self.language = language
        self.logger = get_logger()
        self.ffmpeg_manager = ffmpeg_manager or FFmpegManager()

        if not WHISPER_AVAILABLE:
            raise ImportError("Whisper not available. Please install: pip install openai-whisper")

        # Ensure FFmpeg is available and configure Whisper to use it
        try:
            if self.ffmpeg_manager.ensure_ffmpeg():
                ffmpeg_path = self.ffmpeg_manager.get_ffmpeg_path()
                # Set environment variable so Whisper uses the bundled FFmpeg
                os.environ["FFMPEG_BINARY"] = ffmpeg_path
                self.logger.info("Using bundled FFmpeg")
                try:
                    # whisper.audio caches the path at import time, so update it explicitly
                    whisper.audio.FFMPEG = ffmpeg_path
                except Exception as e:
                    self.logger.warning(f"Failed to update Whisper FFmpeg path: {e}")
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
            # Convert to long path to avoid issues with Windows 8.3 format
            long_audio_path = get_long_path(audio_path)
            self.logger.info(f"Starting transcription: {long_audio_path}")
            start_time = time.time()
            
            # Verify file exists and is accessible
            if not os.path.exists(long_audio_path):
                raise FileNotFoundError(f"Audio file not found: {long_audio_path}")
                
            # Check file is readable and has content
            try:
                file_size = os.path.getsize(long_audio_path)
                if file_size == 0:
                    raise ValueError(f"Audio file is empty: {long_audio_path}")
                
                # Try to open the file to check if it's accessible
                with open(long_audio_path, 'rb') as f:
                    # Read a small chunk to ensure file is readable
                    f.read(1024)
                
                self.logger.info(f"Audio file verified: {long_audio_path} ({file_size} bytes)")
                
                # Small delay to ensure file is fully accessible
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Audio file access error: {str(e)}")
                raise
            
            # Progress callback for initial setup
            if progress_callback:
                progress_callback(0, "Loading audio...")
            
            # Использование абсолютного пути и настройка параметров whisper
            # Добавим явную настройку для FFmpeg
            try:
                # Устанавливаем вручную путь к FFmpeg для Whisper
                ffmpeg_path = self.ffmpeg_manager.get_ffmpeg_path()
                os.environ["FFMPEG_BINARY"] = ffmpeg_path
                
                # Загружаем аудио напрямую через встроенную библиотеку wave и numpy
                self.logger.info(f"Loading audio directly: {long_audio_path}")
                try:
                    # Загружаем WAV файл напрямую
                    import wave
                    from whisper.audio import log_mel_spectrogram, pad_or_trim
                    
                    # Чтение аудио файла напрямую с помощью модуля wave
                    self.logger.info("Reading WAV file...")
                    with wave.open(long_audio_path, 'rb') as wav_file:
                        sample_rate = wav_file.getframerate()
                        n_channels = wav_file.getnchannels()
                        sample_width = wav_file.getsampwidth()  # in bytes
                        n_frames = wav_file.getnframes()
                        
                        # Чтение всех фреймов
                        raw_data = wav_file.readframes(n_frames)
                    
                    # Конвертируем байты в числа используя numpy
                    if sample_width == 1:  # 8-bit unsigned
                        audio_data = np.frombuffer(raw_data, dtype=np.uint8)
                        # Нормализация: от [0, 255] к [-1.0, 1.0]
                        audio_data = (audio_data.astype(np.float32) - 128) / 128.0
                    elif sample_width == 2:  # 16-bit signed
                        audio_data = np.frombuffer(raw_data, dtype=np.int16)
                        # Нормализация: от [-32768, 32767] к [-1.0, 1.0]
                        audio_data = audio_data.astype(np.float32) / 32768.0
                    elif sample_width == 4:  # 32-bit signed
                        audio_data = np.frombuffer(raw_data, dtype=np.int32)
                        # Нормализация: от [-2^31, 2^31-1] к [-1.0, 1.0]
                        audio_data = audio_data.astype(np.float32) / 2147483648.0
                    
                    self.logger.info(f"Audio loaded, sample rate: {sample_rate}, channels: {n_channels}, length: {len(audio_data)}")
                    
                    # Если стерео, разбиваем каналы и усредняем
                    if n_channels > 1:
                        # Раскладываем данные по каналам и усредняем
                        audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)
                        
                    # Whisper ожидает 16kHz моно float32
                    # Если частота отличается от 16kHz, просто предупредим
                    # Whisper позаботится об этом сам
                    if sample_rate != 16000:
                        self.logger.warning(f"Audio sample rate is {sample_rate}Hz, but Whisper expects 16000Hz")
                        
                    self.logger.info(f"Audio data prepared, length: {len(audio_data)} samples")
                    
                    # Транскрибируем с настройками для timestamps, передавая данные напрямую
                    self.logger.info("Starting Whisper transcription using audio data...")
                    
                    # Если язык указан явно, используем его
                    if self.language:
                        self.logger.info(f"Using specified language: {self.language}")
                        result = self.model.transcribe(
                            audio_data, 
                            word_timestamps=True, 
                            verbose=True,
                            language=self.language  # Явно указываем язык
                        )
                    else:
                        # Автоопределение языка
                        result = self.model.transcribe(audio_data, word_timestamps=True, verbose=True)
                    
                    # Обрабатываем результаты
                    segments = []
                    total_audio_duration = float(result.get('duration', 60.0))  # В секундах, по умолчанию 60 секунд
                    
                    for i, segment in enumerate(result.get('segments', [])):
                        text = segment["text"].strip()
                        start_time = segment["start"]
                        end_time = segment["end"]
                        
                        if self.language == "uk":
                            # Заменяем часто путаемые буквы или слова
                            text = text.replace("и", "і")
                        
                        segments.append({
                            "start": start_time,
                            "end": end_time,
                            "text": text
                        })
                        
                        # Обновляем прогресс на основе текущего тайминга сегмента
                        if progress_callback and total_audio_duration > 0:
                            # Рассчитываем процент готовности на основе времени текущего сегмента
                            # Масштабируем от 30% до 90% всего прогресса (остальное - загрузка и сохранение)
                            segment_progress = min(90, 30 + (end_time / total_audio_duration) * 60)
                            segment_msg = f"Обработано {int(end_time)}/{int(total_audio_duration)} секунд: \"{text}\""
                            progress_callback(int(segment_progress), segment_msg)
                    
                    self.logger.info("Whisper transcription completed successfully")
                except Exception as audio_err:
                    self.logger.error(f"Direct audio loading failed: {str(audio_err)}")
                    raise
                self.logger.info("Whisper transcription completed successfully")
            except Exception as whisper_err:
                self.logger.error(f"Whisper transcription error: {str(whisper_err)}")
                raise
            
            # Progress callback for processing
            if progress_callback:
                progress_callback(50, "Processing segments...")
            
            # Extract segments with timestamps
            # segments = []
            # for segment in result.get('segments', []):
            #     segment_data = {
            #         'start': float(segment.get('start', 0)),
            #         'end': float(segment.get('end', 0)),
            #         'text': str(segment.get('text', '')).strip()
            #     }
                
            #     # Only add non-empty segments
            #     if segment_data['text']:
            #         segments.append(segment_data)
            
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
            # Convert to long path to avoid issues with Windows 8.3 format
            long_audio_path = get_long_path(audio_path)
            
            # Load and transcribe the specific segment
            result = self.model.transcribe(
                long_audio_path,
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
