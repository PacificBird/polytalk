# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Logging utilities for PolyTalk application.

Provides a consistent logging setup across the application.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def _resolve_log_level(default: int = logging.INFO) -> int:
    """Resolve LOG_LEVEL from the environment, falling back to default."""
    level_name = os.environ.get("LOG_LEVEL", "").strip().upper()
    if not level_name:
        return default

    level = logging.getLevelName(level_name)
    if isinstance(level, int):
        return level

    return default


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with consistent configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = _resolve_log_level()
    logger.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    return logger


def setup_file_logger(
    name: str, log_dir: Optional[Path] = None, level: int = logging.INFO
) -> logging.Logger:
    """
    Get a logger instance that also writes to a file.

    Args:
        name: Logger name (usually __name__)
        log_dir: Directory for log files
        level: Logging level

    Returns:
        Configured logger instance with file handler
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    effective_level = _resolve_log_level(level)
    logger.setLevel(effective_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)

    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "polytalk.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(effective_level)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

    return logger
