"""
Video player widget for the transcription application.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QSlider, QLabel, QSizePolicy)
from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtGui import QIcon

from utils.logger import get_logger

class VideoPlayer(QWidget):
    """Custom video player widget with playback controls."""
    
    position_changed = Signal(int)  # Emitted when position changes
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.setup_ui()
        self.setup_player()
        
    def setup_ui(self):
        """Setup the video player UI."""
        layout = QVBoxLayout(self)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_widget)
        
        # Controls layout
        controls_layout = QVBoxLayout()
        
        # Position slider
        slider_layout = QHBoxLayout()
        
        self.position_label = QLabel("00:00:00")
        self.position_label.setMinimumWidth(80)
        slider_layout.addWidget(self.position_label)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(100)
        self.position_slider.setValue(0)
        slider_layout.addWidget(self.position_slider)
        
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setMinimumWidth(80)
        slider_layout.addWidget(self.duration_label)
        
        controls_layout.addLayout(slider_layout)
        
        # Playback controls
        playback_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Play")
        self.play_button.setMinimumHeight(35)
        playback_layout.addWidget(self.play_button)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setMinimumHeight(35)
        self.pause_button.setEnabled(False)
        playback_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False)
        playback_layout.addWidget(self.stop_button)
        
        # Volume control
        playback_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        playback_layout.addWidget(self.volume_slider)
        
        # Speed control
        playback_layout.addWidget(QLabel("Speed:"))
        self.speed_button = QPushButton("1.0x")
        self.speed_button.setMaximumWidth(50)
        playback_layout.addWidget(self.speed_button)
        
        playback_layout.addStretch()
        
        controls_layout.addLayout(playback_layout)
        layout.addLayout(controls_layout)
        
    def setup_player(self):
        """Setup the media player."""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        
        # Connect player to video widget and audio output
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect signals
        self.connect_signals()
        
        # Speed options
        self.speed_options = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.current_speed_index = 2  # 1.0x
        
    def connect_signals(self):
        """Connect player signals and UI controls."""
        # Media player signals
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.update_playback_state)
        
        # UI control signals
        self.play_button.clicked.connect(self.play)
        self.pause_button.clicked.connect(self.pause)
        self.stop_button.clicked.connect(self.stop)
        
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        self.position_slider.valueChanged.connect(self.set_position)
        
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.speed_button.clicked.connect(self.cycle_speed)
        
        # Internal state
        self.slider_pressed_flag = False
        
    def load_video(self, file_path):
        """Load a video file."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Video file not found: {file_path}")
            
            url = QUrl.fromLocalFile(str(Path(file_path).resolve()))
            self.media_player.setSource(url)
            
            # Reset controls
            self.position_slider.setValue(0)
            self.position_label.setText("00:00:00")
            self.duration_label.setText("00:00:00")
            
            self.logger.info(f"Video loaded in player: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load video in player: {str(e)}")
            raise
    
    def play(self):
        """Start playback."""
        self.media_player.play()
    
    def pause(self):
        """Pause playback."""
        self.media_player.pause()
    
    def stop(self):
        """Stop playback."""
        self.media_player.stop()
    
    def seek_to_time(self, seconds):
        """Seek to a specific time in seconds."""
        if self.media_player.duration() > 0:
            position_ms = int(seconds * 1000)
            self.media_player.setPosition(position_ms)
            self.logger.info(f"Seeking to {seconds:.2f} seconds")
    
    def update_position(self, position_ms):
        """Update position slider and label."""
        if not self.slider_pressed_flag:
            if self.media_player.duration() > 0:
                progress = int((position_ms / self.media_player.duration()) * 100)
                self.position_slider.setValue(progress)
            
            self.position_label.setText(self.ms_to_time_string(position_ms))
            self.position_changed.emit(position_ms)
    
    def update_duration(self, duration_ms):
        """Update duration label when media is loaded."""
        self.duration_label.setText(self.ms_to_time_string(duration_ms))
    
    def update_playback_state(self, state):
        """Update button states based on playback state."""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        elif state == QMediaPlayer.PausedState:
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:  # StoppedState
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
    
    def slider_pressed(self):
        """Handle slider press event."""
        self.slider_pressed_flag = True
    
    def slider_released(self):
        """Handle slider release event."""
        self.slider_pressed_flag = False
    
    def set_position(self, progress):
        """Set player position from slider."""
        if self.slider_pressed_flag and self.media_player.duration() > 0:
            position_ms = int((progress / 100) * self.media_player.duration())
            self.media_player.setPosition(position_ms)
    
    def set_volume(self, volume):
        """Set audio volume."""
        self.audio_output.setVolume(volume / 100.0)
    
    def cycle_speed(self):
        """Cycle through playback speeds."""
        self.current_speed_index = (self.current_speed_index + 1) % len(self.speed_options)
        speed = self.speed_options[self.current_speed_index]
        self.media_player.setPlaybackRate(speed)
        self.speed_button.setText(f"{speed}x")
    
    def ms_to_time_string(self, ms):
        """Convert milliseconds to HH:MM:SS format."""
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
