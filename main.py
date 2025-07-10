#!/usr/bin/env python3
"""
Offline Video Transcriber & Searcher
Main entry point for the desktop application.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PySide6.QtCore import QDir, Qt
from gui.main_window import MainWindow
from utils.logger import setup_logger
from utils.log_handler import setup_qt_logger
from utils.ffmpeg_downloader import FFmpegManager

def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    try:
        import whisper
    except ImportError:
        missing_deps.append("whisper")
    
    try:
        import ffmpeg
    except ImportError:
        missing_deps.append("ffmpeg-python")
    
    # Check if FFmpeg is available (will be auto-downloaded if needed)
    try:
        ffmpeg_manager = FFmpegManager()
        if not ffmpeg_manager.is_ffmpeg_available():
            # FFmpeg will be downloaded automatically when needed
            pass
    except Exception:
        # FFmpeg issues will be handled during runtime
        pass
    
    try:
        import pysubs2
    except ImportError:
        missing_deps.append("pysubs2")
    
    if missing_deps:
        return missing_deps
    
    return None

def main():
    """Main application entry point."""
    # Setup basic logging for startup (будет переконфигурирован в MainWindow)
    logger = setup_logger()
    logger.info("Starting Offline Video Transcriber & Searcher")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Video Transcriber")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VideoTranscriber")
    
    # Set application properties
    app.setQuitOnLastWindowClosed(True)
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Missing Dependencies")
        msg.setText(f"Missing required dependencies: {', '.join(missing_deps)}")
        msg.setInformativeText("Please install the missing packages and try again.")
        msg.exec()
        return 1
    
    try:
        # Check and setup FFmpeg
        ffmpeg_manager = FFmpegManager()
        if not ffmpeg_manager.is_ffmpeg_available():
            # Show download dialog
            progress_dialog = QProgressDialog("Preparing FFmpeg...", "Cancel", 0, 100)
            progress_dialog.setWindowTitle("Initial Setup")
            progress_dialog.setWindowModality(Qt.ApplicationModal)
            progress_dialog.show()
            
            def ffmpeg_progress_callback(percentage, message):
                progress_dialog.setValue(percentage)
                progress_dialog.setLabelText(message)
                app.processEvents()
                
                if progress_dialog.wasCanceled():
                    return False
                return True
            
            if not ffmpeg_manager.ensure_ffmpeg(ffmpeg_progress_callback):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("FFmpeg Setup")
                msg.setText("FFmpeg could not be downloaded automatically.")
                msg.setInformativeText("Please install FFmpeg manually or check your internet connection.")
                msg.exec()
            
            progress_dialog.close()
        
        # Create and show main window
        main_window = MainWindow()
        main_window.show()
        
        # Логирование после этого момента будет идти через Qt консоль
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Application Error")
        msg.setText("Failed to start the application.")
        msg.setInformativeText(str(e))
        msg.exec()
        return 1

if __name__ == "__main__":
    sys.exit(main())
