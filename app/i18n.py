# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Catalog-backed localization helpers for the PolyTalk CE UI."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Request

from .config import Config
from .ui_locales import (
    SUPPORTED_UI_LOCALE_CODES,
    UI_LOCALE_NATIVE_NAMES,
)

LOCALE_DIR = Path(__file__).resolve().parent / "locales"
UI_LOCALE_COOKIE_NAME = "polytalk_ui_locale"
logger = logging.getLogger(__name__)


def supported_ui_locales(config: Config) -> list[str]:
    """Return configured UI locales, falling back for minimal test doubles."""
    value = getattr(config, "supported_ui_locales", None)
    if isinstance(value, (list, tuple)):
        filtered = [locale for locale in value if locale in SUPPORTED_UI_LOCALE_CODES]
        if filtered:
            return filtered
    return sorted(SUPPORTED_UI_LOCALE_CODES)


def default_ui_locale(config: Config) -> str:
    """Return configured default UI locale, falling back for minimal test doubles."""
    value = getattr(config, "default_ui_locale", "en")
    return (
        value if isinstance(value, str) and value in SUPPORTED_UI_LOCALE_CODES else "en"
    )


def normalize_locale(value: str | None, supported: set[str]) -> str | None:
    """Return a supported locale code from a raw locale value."""
    if not value:
        return None
    normalized = value.strip().replace("-", "_")
    if normalized in supported:
        return normalized
    base = normalized.split("_", 1)[0]
    if base in supported:
        return base
    return None


def parse_accept_language(value: str | None, supported: set[str]) -> str | None:
    """Resolve the best supported locale from an Accept-Language header."""
    if not value:
        return None
    weighted: list[tuple[float, str]] = []
    for part in value.split(","):
        language, _, params = part.strip().partition(";")
        weight = 1.0
        if params.strip().startswith("q="):
            try:
                weight = float(params.strip()[2:])
            except ValueError:
                weight = 0.0
        weighted.append((weight, language))
    for _weight, language in sorted(weighted, key=lambda item: item[0], reverse=True):
        locale = normalize_locale(language, supported)
        if locale:
            return locale
    return None


def preferred_locale(request: Request, config: Config) -> str:
    """Return the best initial UI locale for a request."""
    supported = set(supported_ui_locales(config))
    return (
        normalize_locale(request.query_params.get("ui_locale"), supported)
        or normalize_locale(request.cookies.get(UI_LOCALE_COOKIE_NAME), supported)
        or parse_accept_language(request.headers.get("accept-language"), supported)
        or default_ui_locale(config)
    )


def ui_locale_options(locale: str, config: Config) -> list[dict[str, str]]:
    """Return UI locales with native labels for the locale selector."""
    return [
        {
            "code": code,
            "label": UI_LOCALE_NATIVE_NAMES.get(code, code),
        }
        for code in supported_ui_locales(config)
    ]


@lru_cache
def load_catalog(locale: str) -> dict[str, Any]:
    """Load a locale catalog from disk."""
    path = LOCALE_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as catalog_file:
        data = json.load(catalog_file)
    return data if isinstance(data, dict) else {}


@lru_cache
def _merged_public_catalog(locale: str) -> dict[str, Any]:
    """Return a cached merged catalog with English fallbacks applied."""
    english = load_catalog("en")
    localized = load_catalog(locale)
    merged = dict(english)
    merged.update({key: value for key, value in localized.items() if key != "_text"})
    text_map = dict(english.get("_text", {}))
    text_map.update(localized.get("_text", {}))
    merged["_text"] = text_map
    return merged


def public_catalog(locale: str, config: Config) -> dict[str, Any]:
    """Return frontend-safe messages with English fallbacks applied."""
    normalized = normalize_locale(locale, set(supported_ui_locales(config))) or "en"
    return _merged_public_catalog(normalized)


def t(key: str, locale: str, config: Config, **params: Any) -> str:
    """Translate a message key and format named parameters."""
    catalog = public_catalog(locale, config)
    value = catalog.get(key)
    if value is None:
        value = catalog.get("_text", {}).get(key)
    if value is None:
        if config.debug:
            logger.warning(
                "Missing UI translation key", extra={"key": key, "locale": locale}
            )
        return key
    if not isinstance(value, str):
        if config.debug:
            logger.warning(
                "UI translation value is not a string",
                extra={"key": key, "locale": locale},
            )
        return key
    try:
        return value.format(**params)
    except (KeyError, ValueError):
        return value
