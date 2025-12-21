import logging


def get_logger(name: str, level=logging.INFO):
    return logging.getLogger(name)
