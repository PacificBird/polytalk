# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Translation service using configurable LLM translation API formats.

Supports both real API and mock mode for testing.
"""

from typing import Any, Optional

import httpx

from .base import BaseTranslationService, TranslationResult
from ..config import get_config
from ..utils.config import get_custom_instruction_max_chars, parse_bool_config
from ..utils.logger import get_logger
from ..utils.sanitize import normalize_instruction

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

PROVIDER_ROUTING_CONFIG_KEYS = frozenset(
    {
        "providers",
        "default_provider",
        "routing",
    }
)


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
        try:
            self.temperature = float(self.config.get("temperature", 0.1))
        except (TypeError, ValueError):
            self.temperature = 0.1
        self.providers = self.config.get("providers", {})
        self.default_provider = self.config.get("default_provider")
        self.routing = self.config.get("routing", [])
        self.context_enabled = parse_bool_config(
            self.config.get("context_enabled"), True
        )
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

        try:
            self.context_payload_warn_chars = int(
                self.config.get("context_payload_warn_chars", 2000)
            )
        except (TypeError, ValueError):
            self.context_payload_warn_chars = 2000

        self.custom_instruction_max_chars = get_custom_instruction_max_chars(
            self.config.get("custom_instruction_max_chars")
        )

        logger.info(
            "TranslationService initialized: "
            f"enabled={self.enabled}, mock_mode={self.mock_mode}, "
            f"api_format={self.api_format}, context_enabled={self.context_enabled}, "
            f"providers={len(self.providers)}, routing_rules={len(self.routing)}"
        )

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[list[dict[str, str]]] = None,
        visual_context: Optional[str] = None,
        custom_instruction: Optional[str] = None,
    ) -> TranslationResult:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            context: Optional prior source/target translations to use as
                read-only context
            visual_context: Optional shared tab/page visual summary to use as
                a read-only hint
            custom_instruction: Optional user-provided translation guidance

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
            return await self._real_translate(
                text,
                source_language,
                target_language,
                context=context,
                visual_context=visual_context,
                custom_instruction=custom_instruction,
            )
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

    def _build_system_prompt(
        self,
        source_language: str,
        target_language: str,
        system_prompt_template: str | None = None,
    ) -> str:
        source_language_name = self._language_display_name(source_language)
        target_language_name = self._language_display_name(target_language)
        return (system_prompt_template or self.system_prompt_template).format(
            source_language=source_language_name,
            target_language=target_language_name,
            source_language_code=source_language,
            target_language_code=target_language,
        )

    def _legacy_provider_config(self) -> dict[str, Any]:
        """Return current flat translation settings as the default provider."""
        return {
            key: value
            for key, value in {
                **self.config,
                "base_url": self.base_url,
                "endpoint": self.endpoint,
                "api_format": self.api_format,
                "api_key": self.api_key,
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "system_prompt": self.system_prompt_template,
            }.items()
            if key not in PROVIDER_ROUTING_CONFIG_KEYS
        }

    def _get_provider_config(self, provider_name: str | None) -> dict[str, Any]:
        """Return provider config merged over flat translation defaults."""
        provider_config = self._legacy_provider_config()
        if not provider_name:
            return provider_config

        configured_provider = self.providers.get(provider_name)
        if configured_provider is None:
            raise ValueError(f"Unknown translation provider '{provider_name}'")
        if not isinstance(configured_provider, dict):
            raise ValueError(
                f"Translation provider '{provider_name}' must be a mapping"
            )

        provider_config.update(configured_provider)
        return provider_config

    def _configured_default_provider_config(self) -> dict[str, Any]:
        """Resolve the configured default provider with flat config fallback."""
        if self.default_provider:
            return self._get_provider_config(str(self.default_provider))
        return self._get_provider_config(None)

    def _normalize_language_code(self, language: str) -> tuple[str, str]:
        """Return normalized exact and base language codes for matching."""
        normalized = (language or "").replace("-", "_").lower()
        return normalized, normalized.split("_", 1)[0]

    def _language_rule_matches(
        self,
        rule_languages: object,
        language: str,
        *,
        rule_index: int | None = None,
        field_name: str = "language",
    ) -> bool:
        """Return whether a routing language field matches a request language."""
        if rule_languages in (None, ""):
            return True

        if isinstance(rule_languages, str):
            languages = [rule_languages]
        elif isinstance(rule_languages, (list, tuple, set)):
            languages = list(rule_languages)
        else:
            logger.warning(
                "Skipping invalid translation routing language matcher: "
                f"index={rule_index} field={field_name} "
                f"type={type(rule_languages).__name__}"
            )
            return False

        if not languages:
            logger.warning(
                "Skipping empty translation routing language matcher: "
                f"index={rule_index} field={field_name}"
            )
            return False

        normalized_language, base_language = self._normalize_language_code(language)
        for configured_language in languages:
            configured = str(configured_language).strip()
            if configured == "*":
                return True
            normalized_configured, _ = self._normalize_language_code(configured)
            if normalized_configured in {normalized_language, base_language}:
                return True
        return False

    def _rule_priority(self, rule: dict[str, Any]) -> int:
        """Parse a routing rule priority with a low-priority fallback."""
        try:
            return int(rule.get("priority", 1000))
        except (TypeError, ValueError):
            return 1000

    def _routing_rule_matches(
        self,
        rule: dict[str, Any],
        source_language: str,
        target_language: str,
        *,
        rule_index: int | None = None,
    ) -> bool:
        source_languages = rule.get("source_langs", rule.get("source_lang"))
        target_languages = rule.get("target_langs", rule.get("target_lang"))
        return self._language_rule_matches(
            source_languages,
            source_language,
            rule_index=rule_index,
            field_name="source_langs",
        ) and self._language_rule_matches(
            target_languages,
            target_language,
            rule_index=rule_index,
            field_name="target_langs",
        )

    def _resolve_provider_config(
        self, source_language: str, target_language: str
    ) -> dict[str, Any]:
        """Resolve translation provider by priority-based language routing."""
        matching_rules = []
        for index, rule in enumerate(self.routing):
            if not isinstance(rule, dict):
                logger.warning(
                    "Skipping invalid translation routing rule: "
                    f"index={index} type={type(rule).__name__}"
                )
                continue
            if not rule:
                logger.warning(
                    f"Skipping empty translation routing rule: index={index}"
                )
                continue
            if self._routing_rule_matches(
                rule, source_language, target_language, rule_index=index
            ):
                matching_rules.append((self._rule_priority(rule), index, rule))

        if not matching_rules:
            return self._configured_default_provider_config()

        _, _, selected_rule = min(matching_rules, key=lambda item: (item[0], item[1]))
        provider_name = selected_rule.get("provider")
        if not provider_name:
            raise ValueError("Translation routing rule is missing provider")

        return self._get_provider_config(str(provider_name))

    def _provider_value(
        self, provider_config: dict[str, Any], key: str, default: str
    ) -> str:
        """Read a string provider value with unresolved env fallback handling."""
        return _config_value(provider_config.get(key), default)

    def _provider_int(
        self, provider_config: dict[str, Any], key: str, default: int
    ) -> int:
        """Read an integer provider value with a safe fallback."""
        try:
            return int(provider_config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _provider_float(
        self, provider_config: dict[str, Any], key: str, default: float
    ) -> float:
        """Read a float provider value with a safe fallback."""
        try:
            return float(provider_config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _build_url(self, provider_config: dict[str, Any] | None = None) -> str:
        """Build the provider URL, substituting {model} when present."""
        provider_config = provider_config or self._legacy_provider_config()
        base_url = self._provider_value(
            provider_config, "base_url", "https://ai.example.com"
        )
        endpoint = self._provider_value(
            provider_config, "endpoint", "/v1/chat/completions"
        )
        model = self._provider_value(provider_config, "model", "qwen3-8b")
        endpoint = endpoint.replace("{model}", model)
        return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _bearer_headers(
        self, provider_config: dict[str, Any] | None = None
    ) -> dict[str, str]:
        provider_config = provider_config or self._legacy_provider_config()
        api_key = self._provider_value(provider_config, "api_key", "")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _format_contextual_user_text(
        self,
        text: str,
        context: Optional[list[dict[str, str]]],
        visual_context: Optional[str] = None,
    ) -> str:
        if not self.context_enabled:
            return text

        sections = []
        visual_context = " ".join((visual_context or "").strip().split())
        if visual_context:
            sections.append(
                "Shared tab/page visual context hint for reference only. "
                "Do not translate this hint; spoken source text wins if it conflicts:\n"
                f"{visual_context}"
            )

        context_lines = []
        for index, item in enumerate(context or [], start=1):
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            if not source and not target:
                continue
            context_lines.append(f"{index}. Source: {source}\n   Translation: {target}")

        if context_lines:
            previous_context = "\n".join(context_lines)
            sections.append(
                f"Previous conversation context for reference only:\n{previous_context}"
            )

        if not sections:
            return text

        return (
            "\n\n".join(sections)
            + "\n\nCurrent text to translate. Translate only this current text; do not "
            "repeat or retranslate the reference context:\n"
            f"{text}"
        )

    def _build_contextual_system_prompt(
        self,
        source_language: str,
        target_language: str,
        context: Optional[list[dict[str, str]]],
        visual_context: Optional[str] = None,
        custom_instruction: Optional[str] = None,
        system_prompt_template: str | None = None,
    ) -> str:
        """Build the system prompt with optional context and user guidance.

        Args:
            source_language: Source language code or name.
            target_language: Target language code or name.
            context: Prior transcript/translation pairs used as read-only context.
            visual_context: Shared tab/page summary used as a read-only hint.
            custom_instruction: User-provided translation guidance.
            system_prompt_template: Optional provider-specific prompt template.

        Returns:
            System prompt for the translation request.
        """
        system_prompt = self._build_system_prompt(
            source_language,
            target_language,
            system_prompt_template=system_prompt_template,
        )
        if custom_instruction:
            system_prompt = (
                f"{system_prompt}\n\nUser translation instruction (high priority): "
                "Follow this user-provided style, tone, terminology, and "
                "speaker-persona guidance for the current translation while "
                "preserving the source meaning. If the source text is "
                "gender-neutral but the instruction specifies speaker gender, "
                "persona, or voice, choose target-language grammar and verb "
                "forms that match that instruction. Do not mention the "
                "instruction or add explanations. Instruction: "
                f"{custom_instruction}"
            )
        if not self.context_enabled or (not context and not visual_context):
            return system_prompt
        return (
            f"{system_prompt}\n\nUse previous conversation and shared visual context only "
            "to resolve pronouns, references, terminology, tone, domain vocabulary, "
            "and fragmented meaning. Treat visual context as a hint only; spoken "
            "source text wins if there is a conflict. Translate only the current text. "
            "Do not repeat, summarize, or retranslate previous context."
        )

    def _build_translation_request(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[list[dict[str, str]]] = None,
        visual_context: Optional[str] = None,
        custom_instruction: Optional[str] = None,
        provider_config: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Build provider-specific request details for a translation call."""
        provider_config = provider_config or self._resolve_provider_config(
            source_language, target_language
        )
        api_format = self._provider_value(provider_config, "api_format", "openai_chat")
        if api_format not in SUPPORTED_API_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_API_FORMATS))
            raise ValueError(
                f"Unsupported translation api_format '{api_format}'. Use one of: {supported}"
            )

        sanitized_custom_instruction = self._sanitize_custom_instruction(
            custom_instruction
        )
        system_prompt = self._build_contextual_system_prompt(
            source_language,
            target_language,
            context,
            visual_context=visual_context,
            custom_instruction=sanitized_custom_instruction,
            system_prompt_template=self._provider_value(
                provider_config, "system_prompt", self.system_prompt_template
            ),
        )
        user_text = self._format_contextual_user_text(
            text, context, visual_context=visual_context
        )
        prompt_chars = len(system_prompt) + len(user_text)
        if (
            self.context_payload_warn_chars > 0
            and prompt_chars > self.context_payload_warn_chars
        ):
            logger.warning(
                "Translation prompt payload is large: "
                f"chars={prompt_chars} threshold={self.context_payload_warn_chars} "
                f"system_chars={len(system_prompt)} user_chars={len(user_text)} "
                f"context_items={len(context or [])} "
                f"visual_context_chars={len(visual_context or '')} "
                f"custom_instruction_chars={len(sanitized_custom_instruction)}"
            )
        url = self._build_url(provider_config)
        model = self._provider_value(provider_config, "model", "qwen3-8b")
        temperature = self._provider_float(provider_config, "temperature", 0.1)
        max_tokens = self._provider_int(provider_config, "max_tokens", 240)
        api_key = self._provider_value(provider_config, "api_key", "")

        if api_format == "openai_chat":
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            return url, self._bearer_headers(provider_config), payload

        if api_format == "openai_responses":
            payload = {
                "model": model,
                "instructions": system_prompt,
                "input": user_text,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            return url, self._bearer_headers(provider_config), payload

        if api_format == "anthropic_messages":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": self._provider_value(
                    provider_config, "anthropic_version", "2023-06-01"
                ),
            }
            payload = {
                "model": model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_text}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            return url, headers, payload

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-goog-api-key"] = api_key
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {"role": "user", "parts": [{"text": user_text}]},
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
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

    def _parse_translation_response(
        self, result: dict[str, Any], provider_config: dict[str, Any] | None = None
    ) -> str:
        """Extract translated text from a provider-specific response body."""
        provider_config = provider_config or self._legacy_provider_config()
        api_format = self._provider_value(provider_config, "api_format", "openai_chat")

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
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[list[dict[str, str]]] = None,
        visual_context: Optional[str] = None,
        custom_instruction: Optional[str] = None,
    ) -> TranslationResult:
        """
        Translate text using the configured real translation API format.

        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            context: Optional prior source/target translations to use as
                read-only context
            visual_context: Optional shared tab/page visual summary to use as
                a read-only hint
            custom_instruction: Optional user-provided translation guidance

        Returns:
            TranslationResult with translated text
        """
        provider_config = self._resolve_provider_config(
            source_language, target_language
        )
        url, headers, payload = self._build_translation_request(
            text,
            source_language,
            target_language,
            context=context,
            visual_context=visual_context,
            custom_instruction=custom_instruction,
            provider_config=provider_config,
        )

        response = await self._http_client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        try:
            result = response.json()
        except Exception as json_err:
            raise Exception(
                f"Failed to parse JSON response: {response.text}"
            ) from json_err

        translated_text = self._parse_translation_response(result, provider_config)
        api_format = self._provider_value(provider_config, "api_format", "openai_chat")
        if not translated_text:
            raise ValueError(f"Empty {api_format} translation response: {result}")

        logger.info(
            f"Real translation complete: {text[:30]}... -> {translated_text[:30]}..."
        )

        return TranslationResult(
            text=translated_text,
            source_language=source_language,
            target_language=target_language,
            success=True,
        )

    def _sanitize_custom_instruction(self, value: Optional[str]) -> str:
        """Normalize and bound user-provided translation guidance."""
        return normalize_instruction(value, self.custom_instruction_max_chars)

    async def close(self) -> None:
        """Close the HTTP client connection pool."""
        if self._http_client:
            await self._http_client.aclose()
            logger.info("TranslationService HTTP client closed")
