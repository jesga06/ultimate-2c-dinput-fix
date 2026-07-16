import logging
import sys


def setup_logger(name, log_file, is_debug, append=False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if is_debug else logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(
        log_file, mode='a' if append else 'w')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
