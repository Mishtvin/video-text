"""
Logging configuration for the application.
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime

from utils.config import get_app_data_dir, ensure_directory

# Global logger instance
_logger = None

def setup_logger(name: str = "VideoTranscriber", level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure the application logger.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    try:
        log_dir = ensure_directory(os.path.join(get_app_data_dir(), "logs"))
        log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    except Exception as e:
        # If file logging fails, just continue with console logging
        logger.warning(f"Failed to setup file logging: {e}")
    
    # Error handler for critical errors
    try:
        error_log_file = os.path.join(log_dir, f"{name}_errors.log")
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
    except Exception:
        # Ignore if error file logging fails
        pass
    
    _logger = logger
    return logger

def get_logger() -> logging.Logger:
    """Get the current logger instance."""
    global _logger
    
    if _logger is None:
        _logger = setup_logger()
    
    return _logger

def log_exception(logger: logging.Logger, message: str = "An error occurred"):
    """Log an exception with traceback."""
    import traceback
    logger.error(f"{message}: {traceback.format_exc()}")

def log_system_info(logger: logging.Logger):
    """Log system information for debugging."""
    import platform
    import psutil
    
    try:
        logger.info("=== System Information ===")
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Python: {platform.python_version()}")
        logger.info(f"CPU Count: {psutil.cpu_count()}")
        logger.info(f"Memory: {psutil.virtual_memory().total // (1024**3)} GB")
        logger.info(f"Available Memory: {psutil.virtual_memory().available // (1024**3)} GB")
        logger.info("=========================")
    except Exception as e:
        logger.warning(f"Failed to log system info: {e}")

def set_log_level(level: int):
    """Set the logging level for all handlers."""
    global _logger
    
    if _logger:
        _logger.setLevel(level)
        for handler in _logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(max(level, logging.INFO))  # Console minimum INFO
            elif isinstance(handler, logging.FileHandler):
                if "error" in handler.baseFilename.lower():
                    handler.setLevel(logging.ERROR)  # Keep error file at ERROR level
                else:
                    handler.setLevel(logging.DEBUG)  # Regular file at DEBUG level

# Convenience functions for common log levels
def debug(message: str):
    """Log debug message."""
    get_logger().debug(message)

def info(message: str):
    """Log info message."""
    get_logger().info(message)

def warning(message: str):
    """Log warning message."""
    get_logger().warning(message)

def error(message: str):
    """Log error message."""
    get_logger().error(message)

def critical(message: str):
    """Log critical message."""
    get_logger().critical(message)
