#!/usr/bin/env python3
"""
Package the Video Transcriber application with bundled FFmpeg.
This script creates a distribution package that includes FFmpeg.
"""

import os
import sys
import shutil
import platform
from pathlib import Path

from utils.ffmpeg_downloader import FFmpegManager
from utils.logger import setup_logger

def main():
    """Package the application with bundled FFmpeg."""
    logger = setup_logger()
    logger.info("Starting application packaging...")
    
    # Create package directory
    package_dir = Path("dist") / "video-transcriber"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy application files
    logger.info("Copying application files...")
    
    # List of files and directories to copy
    files_to_copy = [
        "main.py",
        "core/",
        "gui/", 
        "modules/",
        "utils/",
        "requirements.txt",
        "setup.py",
        "README.md" if os.path.exists("README.md") else None,
        "replit.md"
    ]
    
    for item in files_to_copy:
        if item is None or not os.path.exists(item):
            continue
            
        src = Path(item)
        dst = package_dir / item
        
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    # Download and bundle FFmpeg
    logger.info("Downloading and bundling FFmpeg...")
    
    # Initialize FFmpeg manager with package directory
    ffmpeg_manager = FFmpegManager()
    
    # Override ffmpeg directory to package location
    original_ffmpeg_dir = ffmpeg_manager.ffmpeg_dir
    ffmpeg_manager.ffmpeg_dir = str(package_dir / "bundled" / "ffmpeg")
    ffmpeg_manager.ffmpeg_executable = ffmpeg_manager._get_ffmpeg_executable_path()
    
    def progress_callback(percentage, message):
        print(f"  {percentage:3d}% - {message}")
    
    if ffmpeg_manager.download_ffmpeg(progress_callback):
        logger.info("FFmpeg bundled successfully")
    else:
        logger.warning("Failed to bundle FFmpeg - users will need to install it manually")
    
    # Create launcher script
    launcher_content = f'''#!/usr/bin/env python3
"""
Video Transcriber Application Launcher
"""

import sys
import os
from pathlib import Path

# Add application directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set bundled FFmpeg path
os.environ["FFMPEG_BUNDLED_PATH"] = str(app_dir / "bundled" / "ffmpeg")

# Launch the application
if __name__ == "__main__":
    from main import main
    sys.exit(main())
'''
    
    launcher_path = package_dir / "run_video_transcriber.py"
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    
    # Make launcher executable on Unix systems
    if platform.system() != "Windows":
        os.chmod(launcher_path, 0o755)
    
    # Create installation script
    install_script = f'''#!/bin/bash
# Video Transcriber Installation Script

echo "Installing Video Transcriber..."

# Install Python dependencies
pip install -r requirements.txt

echo "Installation complete!"
echo "To run the application: python run_video_transcriber.py"
'''
    
    install_path = package_dir / "install.sh"
    with open(install_path, 'w', encoding='utf-8') as f:
        f.write(install_script)
    
    if platform.system() != "Windows":
        os.chmod(install_path, 0o755)
    
    # Create Windows batch file
    if platform.system() == "Windows":
        batch_content = '''@echo off
echo Installing Video Transcriber...
pip install -r requirements.txt
echo Installation complete!
echo To run the application: python run_video_transcriber.py
pause
'''
        batch_path = package_dir / "install.bat"
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
    
    # Create README for the package
    package_readme = f'''# Video Transcriber - Portable Package

This is a portable package of Video Transcriber with bundled FFmpeg.

## Quick Start

1. Install Python dependencies:
   - Linux/macOS: `./install.sh`
   - Windows: `install.bat`

2. Run the application:
   ```
   python run_video_transcriber.py
   ```

## What's Included

- Complete Video Transcriber application
- Bundled FFmpeg (no separate installation needed)
- All required Python packages listed in requirements.txt

## System Requirements

- Python 3.11 or higher
- 4+ GB RAM
- Internet connection (for initial Whisper model download)

## Features

- Offline video transcription using OpenAI Whisper
- Automatic subtitle generation (SRT/VTT)
- Full-text search through transcriptions
- Built-in video player
- No external FFmpeg installation required

For more information, see replit.md
'''
    
    readme_path = package_dir / "README_PACKAGE.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(package_readme)
    
    logger.info(f"Package created successfully: {package_dir}")
    logger.info("Package contents:")
    for root, dirs, files in os.walk(package_dir):
        level = root.replace(str(package_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")

if __name__ == "__main__":
    main()