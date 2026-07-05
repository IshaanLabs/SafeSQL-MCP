import logging
from logging.handlers import RotatingFileHandler
from logger.config import LOG_FILE_PATH, LOG_FORMAT, DATE_FORMAT, MAX_LOG_FILE_SIZE_MB, BACKUP_COUNT

def get_logger(name: str = "project_logger") -> logging.Logger:
    """
    Creates and returns a configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create a rotating file handler
    file_handler = RotatingFileHandler(
        filename=LOG_FILE_PATH,
        maxBytes=MAX_LOG_FILE_SIZE_MB * 1024 * 1024,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )

    # Formatter
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    # Optional: Add stream (console) logging for development
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False

    return logger
