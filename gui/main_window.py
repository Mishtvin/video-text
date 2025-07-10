"""
Main window GUI for the Video Transcriber application.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLineEdit, QTextEdit, QProgressBar,
                              QFileDialog, QLabel, QSplitter, QGroupBox,
                              QMessageBox, QStatusBar)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

from gui.video_player import VideoPlayer
from core.controller import TranscriptionController
from utils.logger import get_logger

class TranscriptionWorker(QThread):
    """Worker thread for video transcription to prevent GUI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    transcription_completed = Signal(bool, str)  # success, message
    
    def __init__(self, controller, video_path):
        super().__init__()
        self.controller = controller
        self.video_path = video_path
        self.logger = get_logger()
    
    def run(self):
        """Run the transcription process."""
        try:
            self.progress_updated.emit(10, "Extracting audio...")
            audio_path = self.controller.extract_audio(self.video_path, self.audio_progress_callback)
            
            self.progress_updated.emit(30, "Starting transcription...")
            segments = self.controller.transcribe_audio(audio_path, self.progress_callback)
            
            self.progress_updated.emit(90, "Generating subtitles...")
            subtitle_path = self.controller.generate_subtitles(segments, self.video_path)
            
            self.progress_updated.emit(95, "Indexing for search...")
            self.controller.index_segments(segments, self.video_path)
            
            self.progress_updated.emit(100, "Transcription completed!")
            self.transcription_completed.emit(True, f"Transcription completed. Subtitles saved to: {subtitle_path}")
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            self.transcription_completed.emit(False, f"Transcription failed: {str(e)}")
    
    def progress_callback(self, percentage, message=""):
        """Callback for transcription progress updates."""
        progress = 30 + int(percentage * 0.6)  # Map 0-100% to 30-90%
        self.progress_updated.emit(progress, message or "Transcribing...")
    
    def audio_progress_callback(self, percentage, message=""):
        """Callback for audio extraction progress updates."""
        progress = 10 + int(percentage * 0.2)  # Map 0-100% to 10-30%
        self.progress_updated.emit(progress, message or "Extracting audio...")

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.controller = TranscriptionController()
        self.current_video_path = None
        self.transcription_worker = None
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Offline Video Transcriber & Searcher")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for video and controls
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Video player
        video_group = QGroupBox("Video Player")
        video_layout = QVBoxLayout(video_group)
        
        self.video_player = VideoPlayer()
        video_layout.addWidget(self.video_player)
        
        splitter.addWidget(video_group)
        
        # Right panel - Controls and search
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout(file_group)
        
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.setMinimumHeight(40)
        file_layout.addWidget(self.load_video_btn)
        
        self.transcribe_btn = QPushButton("Transcribe Video")
        self.transcribe_btn.setMinimumHeight(40)
        self.transcribe_btn.setEnabled(False)
        file_layout.addWidget(self.transcribe_btn)
        
        controls_layout.addWidget(file_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)
        
        controls_layout.addWidget(progress_group)
        
        # Search section
        search_group = QGroupBox("Search Transcription")
        search_layout = QVBoxLayout(search_group)
        
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search phrase...")
        self.search_input.setEnabled(False)
        search_input_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setEnabled(False)
        search_input_layout.addWidget(self.search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # Search results
        self.search_results = QTextEdit()
        self.search_results.setMaximumHeight(200)
        self.search_results.setPlaceholderText("Search results will appear here...")
        search_layout.addWidget(self.search_results)
        
        controls_layout.addWidget(search_group)
        
        # Transcription display
        transcript_group = QGroupBox("Transcription")
        transcript_layout = QVBoxLayout(transcript_group)
        
        self.transcript_display = QTextEdit()
        self.transcript_display.setPlaceholderText("Transcription will appear here after processing...")
        self.transcript_display.setReadOnly(True)
        transcript_layout.addWidget(self.transcript_display)
        
        controls_layout.addWidget(transcript_group)
        
        splitter.addWidget(controls_widget)
        
        # Set splitter proportions (video player gets more space)
        splitter.setSizes([700, 500])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def connect_signals(self):
        """Connect signals and slots."""
        self.load_video_btn.clicked.connect(self.load_video)
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.search_btn.clicked.connect(self.search_transcription)
        self.search_input.returnPressed.connect(self.search_transcription)
        
    def load_video(self):
        """Load a video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*)"
        )
        
        if file_path:
            try:
                self.current_video_path = file_path
                self.video_player.load_video(file_path)
                self.transcribe_btn.setEnabled(True)
                
                # Clear previous results
                self.transcript_display.clear()
                self.search_results.clear()
                self.search_input.setEnabled(False)
                self.search_btn.setEnabled(False)
                
                self.status_bar.showMessage(f"Loaded: {Path(file_path).name}")
                self.logger.info(f"Video loaded: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to load video: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load video:\n{str(e)}")
    
    def start_transcription(self):
        """Start the transcription process."""
        if not self.current_video_path:
            return
        
        # Disable controls during transcription
        self.transcribe_btn.setEnabled(False)
        self.load_video_btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start transcription worker
        self.transcription_worker = TranscriptionWorker(self.controller, self.current_video_path)
        self.transcription_worker.progress_updated.connect(self.update_progress)
        self.transcription_worker.transcription_completed.connect(self.transcription_finished)
        self.transcription_worker.start()
        
        self.status_bar.showMessage("Transcription in progress...")
    
    def update_progress(self, percentage, message):
        """Update progress bar and status."""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
        self.status_bar.showMessage(message)
    
    def transcription_finished(self, success, message):
        """Handle transcription completion."""
        # Re-enable controls
        self.transcribe_btn.setEnabled(True)
        self.load_video_btn.setEnabled(True)
        
        # Hide progress
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            # Enable search
            self.search_input.setEnabled(True)
            self.search_btn.setEnabled(True)
            
            # Display transcription
            try:
                segments = self.controller.get_transcription_segments(self.current_video_path)
                transcript_text = "\n".join([f"[{self.format_time(seg['start'])} - {self.format_time(seg['end'])}] {seg['text']}" for seg in segments])
                self.transcript_display.setPlainText(transcript_text)
            except Exception as e:
                self.logger.error(f"Failed to display transcription: {str(e)}")
            
            self.status_bar.showMessage("Transcription completed successfully")
            QMessageBox.information(self, "Success", message)
        else:
            self.status_bar.showMessage("Transcription failed")
            QMessageBox.critical(self, "Transcription Failed", message)
    
    def search_transcription(self):
        """Search through the transcription."""
        query = self.search_input.text().strip()
        if not query:
            return
        
        try:
            results = self.controller.search_transcription(self.current_video_path, query)
            
            if results:
                # Format and display results
                result_text = ""
                for i, result in enumerate(results[:10], 1):  # Limit to 10 results
                    start_time = self.format_time(result['start'])
                    end_time = self.format_time(result['end'])
                    text = result['text']
                    result_text += f"{i}. [{start_time} - {end_time}] {text}\n\n"
                
                self.search_results.setPlainText(result_text)
                
                # Jump to first result
                if results:
                    self.video_player.seek_to_time(results[0]['start'])
                
                self.status_bar.showMessage(f"Found {len(results)} results for '{query}'")
            else:
                self.search_results.setPlainText(f"No results found for '{query}'")
                self.status_bar.showMessage("No results found")
                
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            QMessageBox.critical(self, "Search Error", f"Search failed:\n{str(e)}")
    
    def format_time(self, seconds):
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def closeEvent(self, event):
        """Handle application close event."""
        if self.transcription_worker and self.transcription_worker.isRunning():
            reply = QMessageBox.question(
                self, 
                "Transcription in Progress",
                "Transcription is still running. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.transcription_worker.terminate()
                self.transcription_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
