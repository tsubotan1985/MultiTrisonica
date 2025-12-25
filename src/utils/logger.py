"""
Logging configuration for Multi-Trisonica GUI Application
Provides centralized logging with rotating file handlers
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class AppLogger:
    """
    Application logger with rotating file handler and console output
    """
    
    _initialized = False
    _log_dir = Path("logs")
    
    @classmethod
    def setup_logging(cls, level: int = logging.INFO, log_dir: Optional[Path] = None) -> None:
        """
        Set up application-wide logging configuration
        
        Args:
            level: Logging level (default: INFO)
            log_dir: Directory for log files (default: ./logs)
        """
        if cls._initialized:
            return
        
        if log_dir:
            cls._log_dir = Path(log_dir)
        
        # Create logs directory if it doesn't exist
        cls._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            fmt='%(levelname)s: %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Rotating file handler (10MB max, 5 backups)
        log_file = cls._log_dir / "multitrisonica.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # File gets all messages
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Crash log handler (ERROR and above only)
        crash_log = cls._log_dir / "crash.log"
        crash_handler = logging.handlers.RotatingFileHandler(
            filename=crash_log,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        crash_handler.setLevel(logging.ERROR)
        crash_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(crash_handler)
        
        cls._initialized = True
        
        logging.info("Logging system initialized")
        logging.info(f"Log directory: {cls._log_dir.absolute()}")
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module
        
        Args:
            name: Logger name (typically __name__ of the module)
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name)


# Convenience function
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return AppLogger.get_logger(name)
