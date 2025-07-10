# Offline Video Transcriber & Searcher

## Overview

This is a desktop application built with PySide6 that provides offline video transcription and search capabilities. The application extracts audio from video files, transcribes speech to text using OpenAI Whisper, generates subtitles, and enables full-text search through transcriptions. All processing is done locally without requiring internet connectivity.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

**July 10, 2025:**
- ✅ Completed full project setup with all Python modules
- ✅ Created requirements.txt with all necessary dependencies
- ✅ Added setup.py for package installation 
- ✅ All core modules implemented and ready for deployment:
  - Main application (main.py)
  - GUI components (main_window.py, video_player.py)
  - Processing modules (extractor.py, transcriber.py, subtitler.py, indexer.py)
  - Utility modules (config.py, logger.py)
  - Controller coordination (controller.py)
- 🎯 Project is ready for local download and one-command installation

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **GUI Layer**: PySide6-based desktop interface with video player and controls
- **Core Controller**: Orchestrates the transcription workflow and coordinates between modules
- **Processing Modules**: Specialized modules for audio extraction, speech recognition, subtitle generation, and search indexing
- **Utilities**: Logging, configuration, and helper functions

## Key Components

### Frontend Architecture
- **Main Window** (`gui/main_window.py`): Primary application interface with transcription controls and search functionality
- **Video Player** (`gui/video_player.py`): Custom video player widget with playback controls and subtitle display
- **Worker Threads**: Asynchronous processing to prevent GUI freezing during transcription

### Backend Architecture
- **Audio Extractor** (`modules/extractor.py`): Uses FFmpeg to extract mono WAV audio at 16kHz from video files
- **Speech Transcriber** (`modules/transcriber.py`): Implements OpenAI Whisper for offline speech-to-text conversion
- **Subtitle Generator** (`modules/subtitler.py`): Creates SRT/VTT subtitle files using pysubs2
- **Search Indexer** (`modules/indexer.py`): SQLite database with FTS5 for full-text search capabilities

### Core Controller
- **TranscriptionController** (`core/controller.py`): Central coordinator that manages the entire transcription pipeline and handles inter-module communication

## Data Flow

1. **Video Loading**: User selects video file through file dialog
2. **Audio Extraction**: FFmpeg extracts mono 16kHz WAV audio from video
3. **Speech Recognition**: Whisper processes audio to generate timestamped text segments
4. **Subtitle Generation**: Text segments are formatted into SRT/VTT subtitle files
5. **Search Indexing**: Segments are stored in SQLite FTS5 database for fast text search
6. **Playback & Search**: Users can play video with subtitles and search through transcribed content

## External Dependencies

### Core Libraries
- **PySide6**: Cross-platform GUI framework for desktop interface
- **OpenAI Whisper**: Local speech recognition model (offline capability)
- **FFmpeg**: Video/audio processing via ffmpeg-python wrapper
- **pysubs2**: Subtitle file generation and manipulation
- **SQLite**: Built-in database with FTS5 extension for search functionality

### System Requirements
- FFmpeg must be installed and accessible in system PATH
- Sufficient disk space for temporary audio files and Whisper models
- GPU acceleration optional but recommended for faster transcription

## Deployment Strategy

### Packaging Approach
- **PyInstaller**: Planned for creating standalone executables
- **Cross-platform**: Supports Windows, macOS, and Linux deployment
- **Bundle Strategy**: Single executable with embedded dependencies

### Application Data
- **Configuration**: Platform-specific application data directories
  - Windows: `%APPDATA%/VideoTranscriber`
  - macOS: `~/Library/Application Support/VideoTranscriber`
  - Linux: `~/.local/share/VideoTranscriber`
- **Database**: SQLite file stored in application data directory
- **Temporary Files**: System temp directory for audio extraction

### Key Architectural Decisions

**Speech Recognition Choice**: OpenAI Whisper was selected for its offline capability, multilingual support, and high accuracy. The modular design allows for easy substitution with alternatives like Vosk or Coqui STT.

**Database Selection**: SQLite with FTS5 provides fast full-text search without requiring external database servers, making the application truly portable and offline-capable.

**GUI Framework**: PySide6 offers robust cross-platform desktop capabilities with built-in multimedia support for video playback and modern UI components.

**Audio Processing**: FFmpeg standardizes audio format (mono 16kHz WAV) for optimal speech recognition performance while supporting virtually all video formats.

**Threading Strategy**: Worker threads prevent GUI freezing during long-running transcription tasks while providing progress feedback to users.