import logging
import os

import config
from backend.services import runtime_settings

LOG_DIR = getattr(config, "LOGS_DIR", "logs")
LOG_FILE = "app.log"


def get_logger(name: str) -> logging.Logger:
    # Ensure logs directory exists
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger(name)
    debug_on = bool(runtime_settings.get_debug_mode()) or bool(os.getenv("LEADPILOT_DEBUG", "").strip())
    level = logging.DEBUG if debug_on else logging.INFO

    # Prevent duplicate handlers (important in larger apps)
    if logger.handlers:
        logger.setLevel(level)
        for h in logger.handlers:
            h.setLevel(level)
        return logger

    logger.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s"
    )

    # File Handler
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, LOG_FILE))
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger