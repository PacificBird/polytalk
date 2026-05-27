"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Config


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    """Setup test configuration."""
    # Ensure config is reset for tests
    Config._instance = None
    yield
    # Cleanup after tests
    Config._instance = None


@pytest.fixture
def mock_config():
    """Provide mocked configuration."""
    with patch.object(Config, "get_instance") as mock:
        mock_config = MagicMock()
        mock_config.config = {
            "whisper": {
                "api_key": "test_key",
                "base_url": "http://test.com",
                "mock_mode": True,
            },
            "translation": {
                "api_key": "test_key",
                "base_url": "http://test.com",
                "mock_mode": True,
            },
            "tts": {
                "api_key": "test_key",
                "base_url": "http://test.com",
                "mock_mode": True,
            },
            "app": {
                "name": "TestApp",
                "debug": True,
                "host": "localhost",
                "port": 8000,
            },
            "media": {
                "output_dir": "/tmp/test_media",
            },
        }
        mock.return_value = mock_config
        yield mock_config


@pytest.fixture
def sample_wav_data():
    """Provide sample WAV audio data."""
    return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1e\x00\x00\x40\x1e\x00\x00\x02\x00\x08\x00data\x00\x00\x00\x00"


@pytest.fixture
def sample_webm_data():
    """Provide sample WebM audio data."""
    return b"\x1a\x45\xdf\xa3\x93\x42\x82\x88webm"
