import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file: str = 'app.log', level: int = logging.INFO) -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10**6, backupCount=3),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
