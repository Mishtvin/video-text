"""
Main window GUI for the Video Transcriber application.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QProgressBar,
    QComboBox, QTextBrowser, QMenu, QLineEdit, QDockWidget,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QSplitter,
    QGroupBox, QLabel, QStatusBar, QListWidget, QListWidgetItem
)
from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt, QUrl
import logging
from utils.log_handler import QtLogHandler, LogConsoleWidget
from PySide6.QtGui import QFont, QIcon, QDesktopServices

# Класс CustomTextBrowser предотвращает исчезновение текста после клика
class CustomTextBrowser(QTextBrowser):
    """Custom TextBrowser that prevents document loading on link clicks."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)  # Не открывать ссылки автоматически
    
    # Переопределяем метод setSource, который вызывается при клике на ссылку
    def setSource(self, url):
        # Не делаем ничего, это предотвращает очистку текста
        pass

from gui.video_player import VideoPlayer
from core.controller import TranscriptionController
from utils.logger import get_logger

class VideoItemWidget(QWidget):
    """Widget representing a video task with progress."""

    def __init__(self, video_path: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(Path(video_path).name)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

class TranscriptionWorker(QThread):
    """Worker thread for video transcription to prevent GUI freezing."""

    progress_updated = Signal(str, int, str)  # video path, progress, status
    transcription_completed = Signal(str, bool, str)  # video path, success, msg
    
    def __init__(self, controller, video_path, model_name="base", language=None):
        super().__init__()
        self.controller = controller
        self.video_path = video_path
        self.model_name = model_name
        self.language = language
        self.logger = get_logger()
    
    def run(self):
        """Run the transcription process."""
        try:
            self.progress_updated.emit(self.video_path, 10, "Extracting audio...")
            audio_path = self.controller.extract_audio(self.video_path, self.audio_progress_callback)

            self.progress_updated.emit(self.video_path, 30, "Starting transcription...")
            segments = self.controller.transcribe_audio(audio_path, self.model_name, self.language, self.progress_callback)

            self.progress_updated.emit(self.video_path, 90, "Generating subtitles...")
            subtitle_path = self.controller.generate_subtitles(segments, self.video_path)

            self.progress_updated.emit(self.video_path, 95, "Indexing for search...")
            self.controller.index_segments(segments, self.video_path)

            self.progress_updated.emit(self.video_path, 100, "Transcription completed!")
            self.transcription_completed.emit(self.video_path, True, f"Transcription completed. Subtitles saved to: {subtitle_path}")
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            self.transcription_completed.emit(self.video_path, False, f"Transcription failed: {str(e)}")
    
    def progress_callback(self, percentage, message=""):
        """Callback for transcription progress updates."""
        progress = 30 + int(percentage * 0.6)  # Map 0-100% to 30-90%
        self.progress_updated.emit(self.video_path, progress, message or "Transcribing...")
        
        # Добавляем обработку событий UI для обновления в реальном времени
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def audio_progress_callback(self, percentage, message=""):
        """Callback for audio extraction progress updates."""
        progress = 10 + int(percentage * 0.2)  # Map 0-100% to 10-30%
        self.progress_updated.emit(self.video_path, progress, message or "Extracting audio...")
        
        # Добавляем обработку событий UI для обновления в реальном времени
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.logger = get_logger()
        self.logger.info("Starting Offline Video Transcriber & Searcher")
        
        # Initialize controller
        self.controller = TranscriptionController()
        self.current_video_path = None
        self.video_info = {}
        self.search_results = []
        self.video_tasks = {}
        self.workers = {}
        
        # Set up UI
        self.setup_ui()
        
        # Создаем консоль логов
        self.setup_log_console()
        
        # Настраиваем перехват логов
        self.setup_logging()
        
        # Подключаем сигналы и слоты
        self.connect_signals()
        
        # Настраиваем перехват логов
        self.setup_logging()
        
        # Настраиваем статусную строку
        self.statusBar().showMessage("Готов к работе. Выберите видео для начала.")
        
        self.logger.info("Application started successfully")
        
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

        self.add_videos_btn = QPushButton("Add Videos")
        self.add_videos_btn.setMinimumHeight(40)
        file_layout.addWidget(self.add_videos_btn)

        self.add_processed_btn = QPushButton("Add Processed")
        self.add_processed_btn.setMinimumHeight(40)
        file_layout.addWidget(self.add_processed_btn)
        
        # Settings group for transcription
        settings_group = QGroupBox("Transcription Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Whisper Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")  # Default to base model
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        settings_layout.addLayout(model_layout)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Language:")
        self.lang_combo = QComboBox()
        # Common languages with Ukrainian first
        self.lang_combo.addItem("Auto-detect", None)
        self.lang_combo.addItem("Ukrainian", "uk")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Russian", "ru")
        self.lang_combo.setCurrentText("Ukrainian")  # Default to Ukrainian
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        settings_layout.addLayout(lang_layout)
        
        # Add settings group
        file_layout.addWidget(settings_group)
        
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

        # Queue of videos
        queue_group = QGroupBox("Video Queue")
        queue_layout = QVBoxLayout(queue_group)
        self.video_list = QListWidget()
        queue_layout.addWidget(self.video_list)
        controls_layout.addWidget(queue_group)
        
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
        self.search_results_display = CustomTextBrowser()
        self.search_results_display.setPlaceholderText("Search results will appear here...")
        self.search_results_display.anchorClicked.connect(self.handle_transcript_click)
        search_layout.addWidget(self.search_results_display)
        
        # Transcription display
        transcript_group = QGroupBox("Transcription")
        transcript_layout = QVBoxLayout(transcript_group)

        self.transcript_display = CustomTextBrowser()
        self.transcript_display.setPlaceholderText("Transcription will appear here after processing...")
        self.transcript_display.setReadOnly(True)
        self.transcript_display.anchorClicked.connect(self.handle_transcript_click)
        transcript_layout.addWidget(self.transcript_display)

        search_transcript_splitter = QSplitter(Qt.Vertical)
        search_transcript_splitter.addWidget(search_group)
        search_transcript_splitter.addWidget(transcript_group)
        search_transcript_splitter.setSizes([200, 400])

        controls_layout.addWidget(search_transcript_splitter)
        
        splitter.addWidget(controls_widget)
        
        # Set splitter proportions (video player gets more space)
        splitter.setSizes([700, 500])
        
        # Status bar
        # Статусбар
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")
        
    def setup_log_console(self):
        """Создает и настраивает консоль логов"""
        # Создаем докуемое окно для консоли
        self.log_dock = QDockWidget("Консоль логов", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        
        # Создаем виджет для содержимого дока
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        # Создаем консоль логов
        self.log_console = LogConsoleWidget()
        log_layout.addWidget(self.log_console)
        
        # Добавляем кнопку очистки логов
        clear_btn = QPushButton("Очистить логи")
        clear_btn.clicked.connect(self.log_console.clear_logs)
        log_layout.addWidget(clear_btn)
        
        # Устанавливаем виджет в док и добавляем док в главное окно
        self.log_dock.setWidget(log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
    
    def setup_logging(self):
        """Настраивает перехват логов в консоль"""
        # Используем функцию setup_qt_logger для полной настройки логгирования
        from utils.log_handler import setup_qt_logger
        # Перенастраиваем логгер, чтобы он использовал нашу Qt консоль
        self.logger = setup_qt_logger(self.log_console)
        self.logger.info("Настроено логирование в Qt консоль")
        
    def connect_signals(self):
        """Connect UI signals to slots."""
        self.load_video_btn.clicked.connect(self.load_video)
        self.add_videos_btn.clicked.connect(self.add_videos)
        self.add_processed_btn.clicked.connect(self.add_processed_videos)
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.search_btn.clicked.connect(self.search_transcript)
        self.search_input.returnPressed.connect(self.search_transcript)
        self.video_list.itemClicked.connect(self.queue_item_clicked)
        
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
                
                self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
                self.logger.info(f"Video loaded: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to load video: {str(e)}")
                self.show_error("Error", f"Failed to load video:\n{str(e)}")

    def add_videos(self):
        """Add multiple videos to the processing queue."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*)"
        )

        if files:
            for path in files:
                if path in self.video_tasks:
                    continue
                item = QListWidgetItem()
                item.setData(Qt.UserRole, path)
                widget = VideoItemWidget(path)
                item.setSizeHint(widget.sizeHint())
                self.video_list.addItem(item)
                self.video_list.setItemWidget(item, widget)
                self.video_tasks[path] = widget
            if not self.current_video_path:
                self.current_video_path = files[0]
                self.video_player.load_video(files[0])
                self.transcribe_btn.setEnabled(True)

    def add_processed_videos(self):
        """Add already processed videos to the queue without reprocessing."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Processed Videos",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*)"
        )

        if files:
            added = False
            for path in files:
                if path in self.video_tasks:
                    continue
                segments = self.controller.get_transcription_segments(path)
                if not segments:
                    continue
                item = QListWidgetItem()
                item.setData(Qt.UserRole, path)
                widget = VideoItemWidget(path)
                widget.progress.setValue(100)
                item.setSizeHint(widget.sizeHint())
                self.video_list.addItem(item)
                self.video_list.setItemWidget(item, widget)
                self.video_tasks[path] = widget
                added = True

            if added and not self.current_video_path:
                self.current_video_path = files[0]
                self.video_player.load_video(files[0])
                self.search_input.setEnabled(True)
                self.search_btn.setEnabled(True)
                self.transcribe_btn.setEnabled(True)
                self.display_transcription()

    def queue_item_clicked(self, item):
        """Load the selected video in the player."""
        path = item.data(Qt.UserRole)
        if not path:
            return
        try:
            self.current_video_path = path
            self.video_player.load_video(path)
            segments = self.controller.get_transcription_segments(path)
            if segments:
                self.search_input.setEnabled(True)
                self.search_btn.setEnabled(True)
                self.display_transcription()
        except Exception as e:
            self.logger.error(f"Failed to load selected video: {e}")
    
    def start_transcription(self):
        """Start transcription for all queued videos."""
        if not self.video_tasks:
            return

        # Get selected model and language
        model_name = self.model_combo.currentText()
        language = self.lang_combo.currentData()  # None means auto-detect
        language_display = self.lang_combo.currentText()
        
        # Показываем пользователю выбранные настройки
        self.logger.info(f"Начинаем транскрибирование с моделью '{model_name}' и языком '{language_display}'")
        self.statusBar().showMessage(f"Preparing transcription with model {model_name}...")
        
        # Disable controls during transcription
        self.transcribe_btn.setEnabled(False)
        self.load_video_btn.setEnabled(False)
        self.search_btn.setEnabled(False)

        # Clear progress for current video
        self.progress_bar.setValue(0)
        self.transcript_display.clear()
        self.transcript_display.setPlaceholderText(f"Transcribing with model {model_name}...")

        workers_started = False
        for path in list(self.video_tasks.keys()):
            if path in self.workers:
                continue
            if self.controller.indexer.is_video_indexed(path):
                widget = self.video_tasks.get(path)
                if widget:
                    widget.progress.setValue(100)
                continue
            worker = TranscriptionWorker(self.controller, path, model_name, language)
            worker.progress_updated.connect(self.update_task_progress)
            worker.transcription_completed.connect(self.task_finished)
            self.workers[path] = worker
            worker.start()
            workers_started = True

        if workers_started:
            self.progress_bar.setVisible(True)
            self.logger.info("Transcription started for queued videos")
        else:
            self.progress_bar.setVisible(False)
            self.transcribe_btn.setEnabled(True)
            self.load_video_btn.setEnabled(True)
            self.logger.info("All selected videos are already processed")
        
    def update_progress(self, percent, message):
        """Update progress bar during transcription."""
        self.progress_bar.setValue(percent)
        
        # Если есть информация о видео, добавим информацию о времени
        time_info = ""
        if hasattr(self, 'current_video_path') and self.current_video_path and hasattr(self.video_player, 'media_player') and self.video_player.media_player.duration() > 0:
            # Оцениваем, сколько секунд видео было обработано
            video_duration = self.video_player.media_player.duration() / 1000  # Длительность в секундах
            processed_seconds = (video_duration * percent) / 100
            
            # Форматируем время
            processed_formatted = self.format_time(processed_seconds)
            total_formatted = self.format_time(video_duration)
            
            time_info = f" - Обработано {processed_formatted} из {total_formatted}"
        
        if message:
            status_message = f"Progress: {message} ({percent}%){time_info}"
            self.statusBar().showMessage(status_message)
            self.logger.info(f"Transcription progress: {message} ({percent}%){time_info}")

    def update_task_progress(self, video_path, percent, message):
        """Update progress for a specific video task."""
        widget = self.video_tasks.get(video_path)
        if widget:
            widget.progress.setValue(percent)
        if video_path == self.current_video_path:
            self.update_progress(percent, message)
    
    def _single_transcription_finished(self, success, message):
        """Handle completion for the currently loaded video."""
        # Re-enable controls
        self.transcribe_btn.setEnabled(True)
        self.load_video_btn.setEnabled(True)
        
        if not success:
            self.show_error("Transcription Error", message)
            self.statusBar().showMessage(f"Error: {message}")
            self.logger.error(f"Transcription failed: {message}")
            return
        
        self.search_input.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.display_transcription()
        self.statusBar().showMessage("Transcription completed successfully")
        self.progress_bar.setValue(100)
        
        # Update status
        video_name = Path(self.current_video_path).name
        segments = self.controller.get_transcription_segments(self.current_video_path)
        self.logger.info(f"Transcription completed successfully: {len(segments)} segments")
        self.statusBar().showMessage(f"Transcription of '{video_name}' completed: {len(segments)} segments. Ready for search.")

    def task_finished(self, video_path, success, message):
        """Handle completion of a video task."""
        widget = self.video_tasks.get(video_path)
        if widget and success:
            widget.progress.setValue(100)
        if video_path == self.current_video_path:
            self._single_transcription_finished(success, message)
        self.workers.pop(video_path, None)
        if not self.workers:
            self.transcribe_btn.setEnabled(True)
            self.load_video_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def search_transcript(self):
        """Search for query in transcript."""
        query = self.search_input.text().strip()
        if not query or not self.current_video_path:
            return
        
        self.logger.info(f"Searching: '{query}'")
        self.statusBar().showMessage(f"Searching: '{query}'...")
        
        try:
            self.search_results = self.controller.search_transcription(self.current_video_path, query)
            self.display_search_results()
            
            self.logger.info(f"Search completed: '{query}' -> {len(self.search_results)} results")
            self.statusBar().showMessage(f"Search '{query}': found {len(self.search_results)} results")
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            self.show_error("Search Error", f"Failed to search: {str(e)}")
    
    def display_search_results(self):
        """Display search results in the UI."""
        if not self.search_results:
            self.search_results_display.setHtml("<p>No results found.</p>")
            return
            
        # Format and display results
        html_results = []
        for i, result in enumerate(self.search_results[:10], 1):  # Limit to 10 results
            start_time = result['start']
            start_formatted = self.format_time(start_time)
            end_formatted = self.format_time(result['end'])
            text = result['text']
            
            # Create clickable search result
            html_result = f'<p><b>{i}.</b> <a href="seek:{start_time}">[{start_formatted} - {end_formatted}]</a> {text}</p>'
            html_results.append(html_result)
        
        if html_results:
            self.search_results_display.setHtml(f"<h3>Search Results ({len(self.search_results)}):</h3>\n" + "\n".join(html_results))
        else:
            self.search_results_display.setHtml("<p>No results found.</p>")
        
        # Jump to first result for convenience
        if self.search_results:
            self.video_player.seek_to_time(self.search_results[0]['start'])
            self.logger.info(f"Auto-seeking to first result at {self.search_results[0]['start']:.2f} seconds")
            
    def format_time(self, seconds):
        """Format seconds as HH:MM:SS."""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"
    
    def handle_transcript_click(self, url):
        """Handle clicks on transcript links."""
        url_str = url.toString()
        self.logger.info(f"Transcript link clicked: {url_str}")
        
        # Обрабатываем ссылки вида seek:123.45
        if url_str.startswith("seek:"):
            try:
                time_seconds = float(url_str.split(":", 1)[1])
                self.logger.info(f"Seeking to {time_seconds:.2f} seconds")
                self.statusBar().showMessage(f"Seeking to {time_seconds:.2f} seconds")
                self.video_player.seek_to_time(time_seconds)
                
                # Важно: возвращаем False, чтобы сигнализировать, что мы обработали событие
                # и предотвратить дальнейшую обработку
                return False
            except Exception as e:
                self.logger.error(f"Failed to seek: {str(e)}")
                self.statusBar().showMessage(f"Error seeking: {str(e)}")
        
        # Предотвращаем действие по умолчанию
        return True
        
    def display_transcription(self):
        """Display transcription in the UI."""
        if not self.current_video_path:
            return
            
        segments = self.controller.get_transcription_segments(self.current_video_path)
        if not segments:
            self.transcript_display.setHtml("<p>No transcription available.</p>")
            return
            
        # Format and display transcript
        html_segments = []
        for segment in segments:
            start_time = segment['start']
            start_formatted = self.format_time(start_time)
            end_formatted = self.format_time(segment['end'])
            text = segment['text']
            
            # Create clickable transcript
            html_segment = f'<p><a href="seek:{start_time}">[{start_formatted} - {end_formatted}]</a> {text}</p>'
            html_segments.append(html_segment)
        
        self.transcript_display.setHtml(
            f"<h3>Transcript ({len(segments)} segments):</h3>\n" + 
            "\n".join(html_segments)
        )
        self.logger.info(f"Displayed transcript: {len(segments)} segments")
    
    def show_error(self, title, message):
        """Show error dialog."""
        self.logger.error(f"{title}: {message}")
        QMessageBox.critical(self, title, message)
        self.statusBar().showMessage(f"Error: {message}")
    
    def closeEvent(self, event):
        """Handle application close event."""
        running_workers = [w for w in self.workers.values() if w.isRunning()]
        if running_workers:
            reply = QMessageBox.question(
                self,
                "Transcription in Progress",
                "Transcription is still running. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                for w in running_workers:
                    w.terminate()
                    w.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
