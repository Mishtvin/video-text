import logging
import sys
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import QObject, Signal


class QtLogHandler(logging.Handler, QObject):
    """
    Custom log handler that emits signals for each log message.
    This allows log messages to be displayed in the UI.
    """
    log_message_received = Signal(str)
    
    def __init__(self, level=logging.NOTSET):
        QObject.__init__(self)
        logging.Handler.__init__(self, level)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                                            datefmt='%H:%M:%S'))
        
    def emit(self, record):
        """Emit a log message as a signal"""
        try:
            msg = self.format(record)
            self.log_message_received.emit(msg)
        except Exception:
            self.handleError(record)


class LogConsoleWidget(QPlainTextEdit):
    """
    Widget to display log messages in the UI
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)  # Limit number of lines for performance
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #292929;
                color: #f0f0f0;
                font-family: Consolas, Monospace;
                font-size: 10pt;
            }
        """)
        
    def append_log(self, message):
        """Add log message to the console"""
        self.appendPlainText(message)
        # Auto scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_logs(self):
        """Clear all log messages"""
        self.clear()


def setup_qt_logger(console_widget=None):
    """
    Настройка логгера приложения с перенаправлением в Qt консоль вместо стандартной консоли
    
    Args:
        console_widget: Виджет консоли LogConsoleWidget, куда будут направляться логи
        
    Returns:
        Настроенный логгер
    """
    logger_name = "VideoTranscriber"
    logger = logging.getLogger(logger_name)
    
    # Удаляем все существующие обработчики
    for handler in logger.handlers[:]:  # Создаем копию списка перед его изменением
        logger.removeHandler(handler)
    
    # Настраиваем уровень логирования
    logger.setLevel(logging.INFO)
    
    # Если консольный виджет не передан, настраиваем стандартный вывод в консоль
    if console_widget is None:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    else:
        # Создаем и настраиваем обработчик для Qt консоли
        qt_handler = QtLogHandler()
        qt_handler.log_message_received.connect(console_widget.append_log)
        logger.addHandler(qt_handler)
    
    # Отключаем распространение логов к родительским логгерам
    logger.propagate = False
    
    return logger
