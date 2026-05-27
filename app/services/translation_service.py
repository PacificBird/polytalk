# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Translation service using configurable LLM translation API formats.

Supports both real API and mock mode for testing.
"""


from typing import Any

import httpx

from .base import BaseTranslationService, TranslationResult
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


LANGUAGE_DISPLAY_NAMES = {
    "ar": "Arabic",
    "bn": "Bengali",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "es_MX": "Mexican Spanish",
    "fr": "French",
    "gu": "Gujarati",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "ko": "Korean",
    "ml": "Malayalam",
    "mr": "Marathi",
    "nl": "Dutch",
    "nl_BE": "Belgian Dutch",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "ta": "Tamil",
    "te": "Telugu",
    "tr": "Turkish",
    "zh": "Chinese",
}


SUPPORTED_API_FORMATS = {
    "openai_chat",
    "openai_responses",
    "anthropic_messages",
    "gemini_generate_content",
}


def _config_value(value: object, default: str) -> str:
    """Return a default for missing or unresolved ${VAR} config values."""
    if value is None:
        return default
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return default
    return str(value)


class TranslationService(BaseTranslationService):
    """
    Configurable LLM translation service.

    Uses a strict translation prompt with provider-specific request and response
    adapters. Falls back to mock mode when configured or unavailable.
    """

    def __init__(self) -> None:
        """Initialize translation service with configuration."""
        self.config = get_config().translation
        self.enabled = self.config.get("enabled", True)
        self.mock_mode = self.config.get("mock_mode", True)
        self.base_url = _config_value(
            self.config.get("base_url"), "https://ai.example.com"
        )
        self.endpoint = _config_value(
            self.config.get("endpoint"), "/v1/chat/completions"
        )
        self.api_format = _config_value(self.config.get("api_format"), "openai_chat")
        self.api_key = _config_value(self.config.get("api_key"), "")
        self.model = _config_value(self.config.get("model"), "qwen3-8b")
        self.temperature = self.config.get("temperature", 0.1)
        try:
            self.max_tokens = int(self.config.get("max_tokens", 240))
        except (TypeError, ValueError):
            self.max_tokens = 240
        self.system_prompt_template = self.config.get(
            "system_prompt",
            "You are a professional translator. Translate from {source_language} to {target_language}. Write natural, fluent {target_language}. Preserve the meaning only; do not add explanations, summaries, repeated text, or source-language commentary. If the source transcript is fragmented, translate the intended meaning as faithfully as possible. Return ONLY the translation.",
        )

        # Singleton httpx.AsyncClient with connection pooling
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50,
                keepalive_expiry=60.0,
            ),
        )

        logger.info(
            "TranslationService initialized: "
            f"enabled={self.enabled}, mock_mode={self.mock_mode}, "
            f"api_format={self.api_format}"
        )

    async def translate(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationResult:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code

        Returns:
            TranslationResult with translated text
        """
        if not self.enabled:
            logger.warning("Translation service is disabled")
            return TranslationResult(
                text="",
                source_language=source_language,
                target_language=target_language,
                success=False,
                error="Translation service is disabled",
            )

        if self.mock_mode:
            logger.info("Using mock translation")
            return self._mock_translate(text, source_language, target_language)

        try:
            return await self._real_translate(text, source_language, target_language)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                text=text,
                source_language=source_language,
                target_language=target_language,
                success=False,
                error=str(e),
            )

    def _mock_translate(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationResult:
        """
        Generate mock translation for testing.

        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code

        Returns:
            Mock TranslationResult
        """
        mock_translations = {
            ("en", "gu"): "તમે કેમ છો?",
            ("en", "hi"): "आप कैसे हैं?",
            ("en", "es"): "¿Cómo estás?",
            ("en", "fr"): "Comment allez-vous?",
            ("en", "de"): "Wie geht es Ihnen?",
            ("gu", "en"): "How are you?",
            ("hi", "en"): "How are you?",
            ("es", "en"): "How are you?",
            ("fr", "en"): "How are you?",
            ("de", "en"): "How are you?",
        }

        key = (source_language, target_language)
        translated_text = mock_translations.get(key, f"[{target_language}] {text}")

        logger.info(f"Mock translation: {text[:30]}... -> {translated_text[:30]}...")

        return TranslationResult(
            text=translated_text,
            source_language=source_language,
            target_language=target_language,
            success=True,
        )

    def _language_display_name(self, language: str) -> str:
        """Return a prompt-friendly language name for configured language codes."""
        normalized = (language or "").replace("-", "_")
        if normalized in LANGUAGE_DISPLAY_NAMES:
            return LANGUAGE_DISPLAY_NAMES[normalized]

        base_language = normalized.split("_", 1)[0]
        return LANGUAGE_DISPLAY_NAMES.get(base_language, language)

    def _build_system_prompt(self, source_language: str, target_language: str) -> str:
        source_language_name = self._language_display_name(source_language)
        target_language_name = self._language_display_name(target_language)
        return self.system_prompt_template.format(
            source_language=source_language_name,
            target_language=target_language_name,
            source_language_code=source_language,
            target_language_code=target_language,
        )

    def _build_url(self) -> str:
        """Build the provider URL, substituting {model} when present."""
        endpoint = self.endpoint.format(model=self.model)
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _bearer_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_translation_request(
        self, text: str, source_language: str, target_language: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Build provider-specific request details for a translation call."""
        api_format = self.api_format
        if api_format not in SUPPORTED_API_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_API_FORMATS))
            raise ValueError(
                f"Unsupported translation api_format '{api_format}'. Use one of: {supported}"
            )

        system_prompt = self._build_system_prompt(source_language, target_language)
        url = self._build_url()

        if api_format == "openai_chat":
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            return url, self._bearer_headers(), payload

        if api_format == "openai_responses":
            payload = {
                "model": self.model,
                "instructions": system_prompt,
                "input": text,
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
            return url, self._bearer_headers(), payload

        if api_format == "anthropic_messages":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.config.get("anthropic_version", "2023-06-01"),
            }
            payload = {
                "model": self.model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": text}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            return url, headers, payload

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {"role": "user", "parts": [{"text": text}]},
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        return url, headers, payload

    def _extract_text_from_content_blocks(self, blocks: list[Any]) -> str:
        text_parts = []
        for block in blocks:
            if isinstance(block, dict):
                block_text = block.get("text")
                if block_text:
                    text_parts.append(block_text)
        return "".join(text_parts).strip()

    def _parse_translation_response(self, result: dict[str, Any]) -> str:
        """Extract translated text from a provider-specific response body."""
        api_format = self.api_format

        try:
            if api_format == "openai_chat":
                return result["choices"][0]["message"]["content"].strip()

            if api_format == "openai_responses":
                output_text = result.get("output_text")
                if output_text:
                    return output_text.strip()

                text_parts = []
                for output in result.get("output", []):
                    for content in output.get("content", []):
                        if content.get("type") in {"output_text", "text"}:
                            content_text = content.get("text")
                            if content_text:
                                text_parts.append(content_text)
                return "".join(text_parts).strip()

            if api_format == "anthropic_messages":
                return self._extract_text_from_content_blocks(result.get("content", []))

            if api_format == "gemini_generate_content":
                text_parts = []
                for candidate in result.get("candidates", []):
                    content = candidate.get("content", {})
                    text_parts.append(
                        self._extract_text_from_content_blocks(content.get("parts", []))
                    )
                return "".join(text_parts).strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Invalid {api_format} translation response: {result}"
            ) from exc

        raise ValueError(f"Unsupported translation api_format '{api_format}'")

    async def _real_translate(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationResult:
        """
        Translate text using the configured real translation API format.

        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code

        Returns:
            TranslationResult with translated text
        """
        url, headers, payload = self._build_translation_request(
            text, source_language, target_language
        )

        response = await self._http_client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        try:
            result = response.json()
        except Exception as json_err:
            raise Exception(
                f"Failed to parse JSON response: {response.text}"
            ) from json_err

        translated_text = self._parse_translation_response(result)
        if not translated_text:
            raise ValueError(f"Empty {self.api_format} translation response: {result}")

        logger.info(
            f"Real translation complete: {text[:30]}... -> {translated_text[:30]}..."
        )

        return TranslationResult(
            text=translated_text,
            source_language=source_language,
            target_language=target_language,
            success=True,
        )

    async def close(self) -> None:
        """Close the HTTP client connection pool."""
        if self._http_client:
            await self._http_client.aclose()
            logger.info("TranslationService HTTP client closed")
