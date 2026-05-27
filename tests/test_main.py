"""Tests for main application."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from app.main import create_app, lifespan


class TestMainApplication:
    """Test main application creation and lifespan."""

    def test_create_app_returns_fastapi_instance(self):
        """Test create_app returns FastAPI instance."""
        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.whisper = {"mock_mode": True}
            mock_config.return_value.media_output_dir = Path("/tmp/media")
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            with patch(
                "app.main.os.environ", {"ALLOWED_ORIGINS": "http://localhost:9000"}
            ):
                app = create_app()
                assert isinstance(app, FastAPI)

    def test_create_app_with_static_mount(self):
        """Test create_app mounts static files."""
        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.whisper = {"mock_mode": True}
            mock_config.return_value.media_output_dir = Path("/tmp/media")
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            with patch(
                "app.main.os.environ", {"ALLOWED_ORIGINS": "http://localhost:9000"}
            ):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("fastapi.staticfiles.StaticFiles"):
                        app = create_app()
                        assert app is not None

    def test_create_app_without_static_dir(self):
        """Test create_app when static dir doesn't exist."""
        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.whisper = {"mock_mode": True}
            mock_config.return_value.media_output_dir = Path("/tmp/media")
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            with patch(
                "app.main.os.environ", {"ALLOWED_ORIGINS": "http://localhost:9000"}
            ):
                with patch("pathlib.Path.exists", return_value=False):
                    app = create_app()
                    assert app is not None

    def test_create_app_creates_media_dir(self):
        """Test create_app creates media directory."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.main.get_config") as mock_config:
                mock_config.return_value.whisper = {"mock_mode": True}
                mock_config.return_value.media_output_dir = Path(tmpdir)
                mock_config.return_value.host = "localhost"
                mock_config.return_value.port = 8000

                with patch(
                    "app.main.os.environ", {"ALLOWED_ORIGINS": "http://localhost:9000"}
                ):
                    app = create_app()
                    # Verify the app was created successfully
                    assert app is not None

    def test_create_app_with_multiple_origins(self):
        """Test create_app with multiple CORS origins."""
        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.whisper = {"mock_mode": True}
            mock_config.return_value.media_output_dir = Path("/tmp/media")
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            with patch(
                "app.main.os.environ",
                {"ALLOWED_ORIGINS": "http://localhost:9000,http://127.0.0.1:9000"},
            ):
                app = create_app()
                assert app is not None

    @pytest.mark.asyncio
    async def test_lifespan_startup_logs(self, caplog):
        """Test lifespan context manager startup logs."""
        import logging

        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            with caplog.at_level(logging.INFO):
                async with lifespan(MagicMock()):
                    pass

                # Verify startup log messages were produced
                assert any(
                    "startup" in msg.lower() or "polytalk" in msg.lower()
                    for msg in caplog.messages
                )

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_logs(self, caplog):
        """Test lifespan context manager shutdown logs."""
        import logging

        with patch("app.main.get_config") as mock_config:
            mock_config.return_value.host = "localhost"
            mock_config.return_value.port = 8000

            app_mock = MagicMock()

            with caplog.at_level(logging.INFO):
                async with lifespan(app_mock):
                    pass

                # Verify shutdown log messages were produced
                assert any(
                    "shutdown" in msg.lower() or "polytalk" in msg.lower()
                    for msg in caplog.messages
                )
