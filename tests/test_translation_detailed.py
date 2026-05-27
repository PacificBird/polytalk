# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tests for translation service methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import json
import pytest

from app.services.translation_service import TranslationService


class TestTranslationServiceClose:
    """Test translation service close."""

    @pytest.mark.asyncio
    async def test_close_service(self):
        """Test closing translation service."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": True,
            }
            service = TranslationService()

            with patch.object(service._http_client, "aclose", new_callable=AsyncMock):
                await service.close()


class TestTranslationServiceRealTranslateErrorHandling:
    """Test real translation error handling paths."""

    @pytest.mark.asyncio
    async def test_real_translate_json_parse_error(self):
        """Test translation with JSON parse error."""
        from unittest.mock import MagicMock

        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "invalid json"
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None

            with patch.object(service._http_client, "post", return_value=mock_response):
                await service.translate("Hello", "en", "gu")

                call_args = service._http_client.post.call_args
                assert call_args[1]["json"]["max_tokens"] == 240

    @pytest.mark.asyncio
    async def test_mock_translate_different_language_pairs(self):
        """Test mock translation with different language pairs."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": True,
            }
            service = TranslationService()

            test_cases = [
                ("en", "gu", "તમે કેમ છો?"),
                ("en", "hi", "आप कैसे हैं?"),
                ("en", "es", "¿Cómo estás?"),
                ("en", "fr", "Comment allez-vous?"),
                ("en", "de", "Wie geht es Ihnen?"),
                ("gu", "en", "How are you?"),
                ("hi", "en", "How are you?"),
                ("es", "en", "How are you?"),
                ("fr", "en", "How are you?"),
                ("de", "en", "How are you?"),
            ]

            for source, target, expected in test_cases:
                result = service._mock_translate("How are you?", source, target)
                assert result.success is True
                assert result.text == expected

    @pytest.mark.asyncio
    async def test_mock_translate_unknown_language_pair(self):
        """Test mock translation with unknown language pair."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": True,
            }
            service = TranslationService()

            result = service._mock_translate("Hello", "xx", "yy")
            assert result.success is True
            assert result.text == "[yy] Hello"

    @pytest.mark.asyncio
    async def test_translate_disabled_service(self):
        """Test translation when service is disabled."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": False,
                "mock_mode": True,
            }
            service = TranslationService()

            result = await service.translate("Hello", "en", "gu")

            assert result.success is False
            assert "disabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_translate_real_mode_timeout(self):
        """Test real translation with timeout."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            with patch.object(
                service._http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = httpx.TimeoutException("Timeout")

                result = await service.translate("Hello", "en", "gu")

                assert result.success is False
                assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_translate_real_mode_http_error(self):
        """Test real translation with HTTP error."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            with patch.object(
                service._http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = httpx.HTTPError("HTTP Error")

                result = await service.translate("Hello", "en", "gu")

                assert result.success is False

    @pytest.mark.asyncio
    async def test_translate_retry_logic(self):
        """Test translation retry logic on failure."""
        from unittest.mock import MagicMock

        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            call_count = 0

            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise httpx.HTTPError("Temporary error")
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "success"}}]
                }
                return mock_response

            with patch.object(service._http_client, "post", side_effect=mock_post):
                await service.translate("Hello", "en", "gu")

                assert call_count >= 1

    @pytest.mark.asyncio
    async def test_real_translate_with_invalid_max_tokens(self, caplog):
        """Test real translation handles invalid max_tokens."""
        from unittest.mock import MagicMock

        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
                "max_tokens": "invalid",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            assert service.max_tokens == 240

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "result"}}]
            }
            mock_response.raise_for_status.return_value = None

            with patch.object(service._http_client, "post", return_value=mock_response):
                await service.translate("Hello", "en", "gu")

    @pytest.mark.asyncio
    async def test_real_translate_with_system_prompt_template(self):
        """Test real translation uses system prompt template."""
        from unittest.mock import MagicMock

        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
                "system_prompt": "Translate from {source_language} to {target_language}",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "result"}}]
            }
            mock_response.raise_for_status.return_value = None

            with patch.object(service._http_client, "post", return_value=mock_response):
                await service.translate("Hello", "en", "gu")

                call_args = service._http_client.post.call_args
                messages = call_args[1]["json"]["messages"]
                assert "English" in messages[0]["content"]
                assert "Gujarati" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_real_translate_with_gemini_provider(self):
        """Test real translate with Gemini provider."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "gemini",
                "base_url": "https://generativelanguage.googleapis.com",
                "api_key": "test_key",
                "api_format": "gemini_generate_content",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "translated"}]}}]
            }

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_real_translate_with_anthropic_provider(self):
        """Test real translate with Anthropic provider."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "anthropic",
                "base_url": "https://api.anthropic.com",
                "api_key": "test_key",
                "api_format": "anthropic_messages",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"content": [{"text": "translated"}]}

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_real_translate_with_openai_responses_provider(self):
        """Test real translate with OpenAI Responses API provider."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
                "use_responses_api": True,
                "api_format": "openai_responses",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "output": [{"content": [{"type": "output_text", "text": "translated"}]}]
            }
            mock_response.raise_for_status.return_value = None

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_translate_with_empty_text(self):
        """Test translate with empty text."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": True,
            }

            service = TranslationService()
            result = await service.translate("", "en", "gu")

            assert result.success is True
            assert result.text == "તમે કેમ છો?"

    @pytest.mark.asyncio
    async def test_translate_with_whitespace_only(self):
        """Test translate with whitespace only."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": True,
            }

            service = TranslationService()
            result = await service.translate("   ", "en", "gu")

            assert result.success is True
            assert result.text == "તમે કેમ છો?"

    @pytest.mark.asyncio
    async def test_real_translate_with_http_status_401(self):
        """Test real translate handles HTTP 401."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "invalid_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status.side_effect = Exception(
                "401 Client Error: Unauthorized"
            )

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False

    @pytest.mark.asyncio
    async def test_real_translate_with_http_status_429(self):
        """Test real translate handles HTTP 429 rate limit."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.raise_for_status.side_effect = Exception(
                "429 Client Error: Too Many Requests"
            )

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False

    @pytest.mark.asyncio
    async def test_real_translate_with_http_status_503(self):
        """Test real translate handles HTTP 503 service unavailable."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_response.text = "Service unavailable"
            mock_response.raise_for_status.side_effect = Exception(
                "503 Server Error: Service Unavailable"
            )

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False

    @pytest.mark.asyncio
    async def test_real_translate_with_http_status_504(self):
        """Test real translate handles HTTP 504 gateway timeout."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 504
            mock_response.text = "Gateway timeout"
            mock_response.raise_for_status.side_effect = Exception(
                "504 Server Error: Gateway Timeout"
            )

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False

    @pytest.mark.asyncio
    async def test_translate_with_malformed_json_response(self):
        """Test translate with malformed JSON response."""
        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("test", "doc", 0)
            mock_response.raise_for_status.return_value = None

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False

    @pytest.mark.asyncio
    async def test_translate_with_missing_text_field(self):
        """Test translate with missing text field in response."""

        with patch("app.services.translation_service.get_config") as mock_config:
            mock_config.return_value.translation = {
                "enabled": True,
                "mock_mode": False,
                "provider": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "test_key",
            }
            mock_config.return_value.app = {}

            service = TranslationService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"wrong_field": "translated"}

            with patch.object(service._http_client, "post", return_value=mock_response):
                result = await service.translate("Hello", "en", "gu")
                assert result.success is False
