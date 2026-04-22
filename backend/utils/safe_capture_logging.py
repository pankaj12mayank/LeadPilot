"""Logging for the safe manual capture pipeline (separate log file)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import config

LOG_NAME = "safe_capture.log"


def get_safe_capture_logger(name: str) -> logging.Logger:
    log_dir = Path(getattr(config, "LOGS_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_NAME

    logger = logging.getLogger(f"safe_capture.{name}")
    if logger.handlers:
        return logger

    level_name = str(getattr(config, "LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    fh = logging.FileHandler(os.fspath(log_path), encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logger.level)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logger.level)
    logger.addHandler(ch)

    return logger
