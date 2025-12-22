# app/utils/logger.py
import logging

logger = logging.getLogger("afe_backend")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
