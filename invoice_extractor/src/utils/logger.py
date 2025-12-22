# src/utils/logger.py
from __future__ import annotations
import logging
from logging import Logger
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"




import os

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "invoice_extractor.log")
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str = "app", level: str = "INFO") -> Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Handler para consola
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        logger.addHandler(stream_handler)
        # Handler para archivo
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        logger.addHandler(file_handler)
    logger.setLevel(level.upper() if isinstance(level, str) else level)
    return logger


# default module logger
logger = get_logger("invoice_processor")
