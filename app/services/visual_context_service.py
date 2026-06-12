# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Visual context summarization for shared tab/page screenshots."""

import asyncio
from typing import Any, Optional

import httpx

from ..config import get_config
from ..utils.config import parse_bool_config
from ..utils.logger import get_logger
from .translation_service import SUPPORTED_API_FORMATS

logger = get_logger(__name__)

MAX_RETRIES = 3


def _config_value(value: object, default: str) -> str:
    """Return a default for missing or unresolved ${VAR} config values."""
    if value is None:
        return default
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return default
    return str(value)


class VisualContextService:
    """Summarize a shared tab/page screenshot into short translation context."""

    def __init__(self) -> None:
        config = get_config()
        self.config = config.visual_context
        translation_config = config.translation

        self.enabled = parse_bool_config(self.config.get("enabled"), False)
        self.mock_mode = parse_bool_config(
            self.config.get("mock_mode"),
            bool(translation_config.get("mock_mode", True)),
        )
        self.base_url = _config_value(
            self.config.get("base_url"),
            _config_value(translation_config.get("base_url"), "https://ai.example.com"),
        )
        self.endpoint = _config_value(
            self.config.get("endpoint"),
            _config_value(translation_config.get("endpoint"), "/v1/chat/completions"),
        )
        self.api_format = _config_value(
            self.config.get("api_format"),
            _config_value(translation_config.get("api_format"), "openai_chat"),
        )
        self.api_key = _config_value(
            self.config.get("api_key"),
            _config_value(translation_config.get("api_key"), ""),
        )
        self.model = _config_value(
            self.config.get("model"),
            _config_value(translation_config.get("model"), "gpt-4o-mini"),
        )
        try:
            self.temperature = float(
                _config_value(self.config.get("temperature"), "0.0")
            )
        except (TypeError, ValueError):
            self.temperature = 0.0
        self.disable_thinking = parse_bool_config(
            self.config.get("disable_thinking"), True
        )

        try:
            self.max_tokens = int(self.config.get("max_tokens", 240))
        except (TypeError, ValueError):
            self.max_tokens = 240
        try:
            self.max_summary_chars = int(self.config.get("max_summary_chars", 1200))
        except (TypeError, ValueError):
            self.max_summary_chars = 1200
        try:
            self.max_image_chars = int(self.config.get("max_image_chars", 1_500_000))
        except (TypeError, ValueError):
            self.max_image_chars = 1_500_000

        self._http_client = httpx.AsyncClient(timeout=30.0)
        logger.info(
            "VisualContextService initialized: "
            f"enabled={self.enabled}, mock_mode={self.mock_mode}, "
            f"api_format={self.api_format}, model={self.model}"
        )
        if self.enabled and self.mock_mode:
            logger.warning(
                "VisualContextService is in mock mode; no real screenshot "
                "summary API calls will be made. Set VISUAL_CONTEXT_MOCK_MODE=false "
                "and configure visual context provider settings to use real summaries."
            )

    async def summarize_screenshot(
        self,
        image_data_url: str,
        source_language: str,
        target_language: str,
    ) -> Optional[str]:
        """Return a short text summary for a shared tab/page screenshot."""
        if not self.enabled:
            return None
        if not image_data_url or len(image_data_url) > self.max_image_chars:
            logger.warning(
                "Visual context screenshot rejected: "
                f"chars={len(image_data_url or '')} max={self.max_image_chars}"
            )
            return None
        if self.mock_mode:
            return self._trim_summary(
                "The shared tab/page screenshot may contain visible titles, names, "
                "product labels, and domain vocabulary relevant to this live session."
            )

        prompt = self._build_prompt(source_language, target_language)
        try:
            url, headers, payload = self._build_request(image_data_url, prompt)
        except Exception as exc:
            logger.warning(f"Visual context request build failed: {exc}")
            return None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._http_client.post(
                    url, headers=headers, json=payload
                )
                response.raise_for_status()
                summary = self._parse_response(response.json())
                return self._trim_summary(summary)
            except Exception as exc:
                if attempt == MAX_RETRIES - 1:
                    logger.warning(f"Visual context summarization failed: {exc}")
                    return None
                await asyncio.sleep(0.5 * (2**attempt))

        return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

    def _build_prompt(self, source_language: str, target_language: str) -> str:
        return (
            "Analyze this shared browser tab/page screenshot for live speech "
            "translation context. /no_think Do not reason step by step. Do not "
            "include analysis, markdown, JSON, or bullet points. Do not mention "
            "subtitles, captions, transcript text, or existing translations. Return "
            "1-2 concise plain-text sentences, maximum 70 words total. Include the "
            "main page/video/meeting title, topic, visible names, and useful domain "
            "terms or stable on-screen vocabulary. Ignore related/recommended content "
            "unless it is clearly central to the active page. Treat the screenshot as "
            "a hint only; spoken audio is authoritative if it conflicts. "
            f"Source language code: {source_language}. Target language code: {target_language}."
        )

    def _build_url(self) -> str:
        endpoint = self.endpoint.format(model=self.model)
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _bearer_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_request(
        self, image_data_url: str, prompt: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        if self.api_format not in SUPPORTED_API_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_API_FORMATS))
            raise ValueError(
                f"Unsupported visual context api_format '{self.api_format}'. Use one of: {supported}"
            )

        url = self._build_url()
        if self.api_format == "openai_chat":
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You summarize screenshots for live translation context. Return 1-2 concise sentences only.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_data_url}},
                        ],
                    },
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if self.disable_thinking:
                # Qwen/vLLM-compatible chat templates use this to skip reasoning.
                payload["chat_template_kwargs"] = {"enable_thinking": False}
            return url, self._bearer_headers(), payload

        if self.api_format == "openai_responses":
            payload = {
                "model": self.model,
                "instructions": "You summarize screenshots for live translation context. Return 1-2 concise sentences only.",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": image_data_url},
                        ],
                    }
                ],
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
            return url, self._bearer_headers(), payload

        if self.api_format == "anthropic_messages":
            media_type, image_base64 = self._split_data_url(image_data_url)
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.config.get("anthropic_version", "2023-06-01"),
            }
            payload = {
                "model": self.model,
                "system": "You summarize screenshots for live translation context. Return 1-2 concise sentences only.",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                        ],
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            return url, headers, payload

        media_type, image_base64 = self._split_data_url(image_data_url)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": media_type,
                                "data": image_base64,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }
        return url, headers, payload

    def _split_data_url(self, image_data_url: str) -> tuple[str, str]:
        if not image_data_url.startswith("data:") or "," not in image_data_url:
            raise ValueError("visual context image must be a data URL")
        header, image_base64 = image_data_url.split(",", 1)
        media_type = header[5:].split(";", 1)[0] or "image/jpeg"
        return media_type, image_base64

    def _coerce_text_content(self, content: Any) -> str:
        """Extract text from provider content shapes without assuming strings."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        text_parts.append(text)
            return "".join(text_parts)
        if isinstance(content, dict):
            text = content.get("text") or content.get("content")
            return text if isinstance(text, str) else ""
        return str(content)

    def _parse_response(self, result: dict[str, Any]) -> str:
        if self.api_format == "openai_chat":
            choices = result.get("choices") or []
            if not choices:
                logger.warning("Visual context response has no choices")
                return ""
            message = choices[0].get("message") or {}
            text = self._coerce_text_content(message.get("content"))
            if not text:
                text = self._coerce_text_content(message.get("reasoning_content"))
            if not text:
                logger.warning(
                    "Visual context response had no text content: "
                    f"message_keys={sorted(message.keys())} "
                    f"finish_reason={choices[0].get('finish_reason')}"
                )
            return text.strip()

        if self.api_format == "openai_responses":
            output_text = result.get("output_text")
            if output_text:
                return output_text.strip()
            text_parts = []
            for output in result.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        text = content.get("text")
                        if text:
                            text_parts.append(text)
            return "".join(text_parts).strip()

        if self.api_format == "anthropic_messages":
            return "".join(
                block.get("text", "")
                for block in result.get("content", [])
                if isinstance(block, dict)
            ).strip()

        text_parts = []
        for candidate in result.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text:
                    text_parts.append(text)
        return "".join(text_parts).strip()

    def _trim_summary(self, summary: str) -> Optional[str]:
        summary = " ".join((summary or "").strip().split())
        if not summary:
            return None
        if self.max_summary_chars > 0 and len(summary) > self.max_summary_chars:
            return summary[: self.max_summary_chars].rstrip()
        return summary
