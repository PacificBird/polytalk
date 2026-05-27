# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tests for logger utility.
"""

import logging
from pathlib import Path
from unittest.mock import patch

from app.utils.logger import get_logger, setup_file_logger


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger."""
        import logging
        import os

        with patch.dict(os.environ, {"LOG_LEVEL": ""}, clear=False):
            test_logger = logging.getLogger("test.module_new")
            test_logger.handlers.clear()
            test_logger.setLevel(logging.NOTSET)
            test_logger.propagate = True

            logger = get_logger("test.module_new")

            assert logger is not None
            assert isinstance(logger, logging.Logger)
            assert logger.name == "test.module_new"
            assert logger.level == logging.INFO

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same instance."""
        logger1 = get_logger("test.module2")
        logger2 = get_logger("test.module2")

        assert logger1 is logger2

    def test_get_logger_console_handler(self):
        """Test that get_logger adds console handler."""
        logger = get_logger("test.module3")

        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


class TestSetupFileLogger:
    """Test setup_file_logger function."""

    def test_setup_file_logger_without_dir(self):
        """Test setup_file_logger without log directory."""
        logger = setup_file_logger("test.file1")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert len(logger.handlers) > 0

    def test_setup_file_logger_with_dir(self):
        """Test setup_file_logger with log directory."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            logger = setup_file_logger("test.file2", log_dir=log_dir)

            assert logger is not None
            assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

            log_file = log_dir / "polytalk.log"
            assert log_file.exists()

    def test_setup_file_logger_creates_dir(self):
        """Test that setup_file_logger creates the directory."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "new_subdir"
            setup_file_logger("test.file3", log_dir=log_dir)

            assert log_dir.exists()
