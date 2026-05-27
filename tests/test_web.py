# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tests for web router.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestWebRouter:
    """Test web router endpoints."""

    def test_home_page(self, client):
        """Test home page rendering."""
        with patch("app.routers.web.get_config") as mock_config:
            mock_config.return_value.app = {
                "auto_play_audio": True,
                "name": "PolyTalk",
            }

            response = client.get("/")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
