"""Tests for logger utilities."""

import logging
import os
from pathlib import Path
from unittest.mock import patch


from app.utils.logger import _resolve_log_level, get_logger, setup_file_logger


class TestLoggerUtilities:
    """Test logger utility functions."""

    def test_resolve_log_level_default(self):
        """Test resolve log level with no env var."""
        with patch.dict(os.environ, {}, clear=True):
            level = _resolve_log_level()
            assert level == logging.INFO

    def test_resolve_log_level_from_env(self):
        """Test resolve log level from environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            level = _resolve_log_level()
            assert level == logging.DEBUG

    def test_resolve_log_level_with_lowercase(self):
        """Test resolve log level with lowercase."""
        with patch.dict(os.environ, {"LOG_LEVEL": "warning"}):
            level = _resolve_log_level()
            assert level == logging.WARNING

    def test_resolve_log_level_with_invalid(self):
        """Test resolve log level with invalid value."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = _resolve_log_level()
            assert level == logging.INFO

    def test_resolve_log_level_with_empty(self):
        """Test resolve log level with empty string."""
        with patch.dict(os.environ, {"LOG_LEVEL": ""}):
            level = _resolve_log_level()
            assert level == logging.INFO

    def test_resolve_log_level_with_whitespace(self):
        """Test resolve log level with whitespace."""
        with patch.dict(os.environ, {"LOG_LEVEL": "  ERROR  "}):
            level = _resolve_log_level()
            assert level == logging.ERROR

    def test_get_logger_returns_logger(self):
        """Test get logger returns logger instance."""
        logger = get_logger("test_module")
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_get_logger_reuses_existing(self):
        """Test get logger reuses existing logger."""
        logger1 = get_logger("test_reuse")
        logger2 = get_logger("test_reuse")
        assert logger1 is logger2

    def test_get_logger_with_different_levels(self):
        """Test get logger with different log levels."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = get_logger("test_debug")
            assert logger.level == logging.DEBUG

    def test_setup_file_logger_returns_logger(self):
        """Test setup file logger returns logger instance."""
        logger = setup_file_logger("test_file", log_dir=None)
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_setup_file_logger_creates_dir(self):
        """Test setup file logger creates log directory."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("logging.FileHandler"):
                logger = setup_file_logger(
                    "test_file_dir", log_dir=Path("/tmp/test_logs")
                )
                mock_mkdir.assert_called_once()
                assert logger is not None

    def test_setup_file_logger_with_existing_handlers(self):
        """Test setup file logger with existing handlers."""
        logger = setup_file_logger("test_existing")
        logger2 = setup_file_logger("test_existing")
        assert logger is logger2

    def test_setup_file_logger_with_custom_level(self):
        """Test setup file logger with custom level."""
        logger = setup_file_logger("test_custom_level", level=logging.WARNING)
        assert logger is not None
