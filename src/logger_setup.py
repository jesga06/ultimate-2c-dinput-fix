import logging
import sys


def setup_logger(name: str, log_file: str, is_debug: bool, append: bool = False) -> logging.Logger:
    """
    Configures and returns a logging.Logger instance with file handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if is_debug else logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(
        log_file, mode='a' if append else 'w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

