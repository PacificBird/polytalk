"""UI localization tests for PolyTalk CE."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.i18n as i18n
from app.config import SUPPORTED_UI_LOCALE_CODES, Config
from app.i18n import (
    normalize_locale,
    parse_accept_language,
    public_catalog,
    t,
    ui_locale_options,
)
from app.ui_locales import UI_LOCALE_NATIVE_NAMES
from app.main import app


def test_accept_language_normalizes_supported_locale():
    supported = set(SUPPORTED_UI_LOCALE_CODES)

    assert parse_accept_language("de-DE,de;q=0.9,en;q=0.8", supported) == "de"
    assert normalize_locale("es-MX", supported) == "es"


def test_translation_falls_back_to_english():
    config = Config()

    assert t("app.title", "de", config)
    assert t("missing.key", "de", config) == "missing.key"


def test_empty_string_translation_is_not_treated_as_missing(monkeypatch):
    config = Config()

    monkeypatch.setattr(
        i18n,
        "public_catalog",
        lambda _locale, _config: {
            "empty.top": "",
            "_text": {"empty.top": "fallback", "empty.text": ""},
        },
    )

    assert t("empty.top", "en", config) == ""
    assert t("empty.text", "en", config) == ""


def test_public_catalog_is_cached_for_normalized_locale():
    config = Config()

    assert public_catalog("de", config) is public_catalog("de-DE", config)


def test_home_uses_query_locale():
    client = TestClient(app)

    response = client.get("/?ui_locale=de")

    assert response.status_code == 200
    assert '<html lang="de">' in response.text
    assert "window.POLYTALK_I18N" in response.text
    assert 'id="ui-locale-select"' in response.text


def test_home_uses_ui_locale_cookie():
    client = TestClient(app)
    client.cookies.set("polytalk_ui_locale", "es")

    response = client.get("/")

    assert response.status_code == 200
    assert '<html lang="es">' in response.text


def test_home_uses_accept_language_locale():
    client = TestClient(app)

    response = client.get("/", headers={"Accept-Language": "fr-FR,fr;q=0.9"})

    assert response.status_code == 200
    assert '<html lang="fr">' in response.text


def test_ui_locale_options_use_native_language_names():
    config = Config()

    labels = {
        option["code"]: option["label"] for option in ui_locale_options("pl", config)
    }

    assert labels == UI_LOCALE_NATIVE_NAMES
    assert labels["en"] == "English"
    assert labels["pl"] == "Polski"
    assert labels["nl"] == "Nederlands"


def test_non_english_catalogs_translate_ce_live_controls():
    config = Config()
    keys = {
        "Live Transcript",
        "Live Translate (Microphone)",
        "Live Translation",
        "Microphone access granted! Ready for live translation.",
        "Microphone ready",
        "Select Microphone",
        "Swap Languages",
        "Swap is disabled in live and conversation modes.",
        'Tab audio sharing is not supported on mobile devices. Please use "Live Translate (Microphone)" instead, or switch to a desktop browser.',
        "UI Language",
    }

    for locale in set(SUPPORTED_UI_LOCALE_CODES) - {"en"}:
        catalog = public_catalog(locale, config)
        for key in keys:
            assert catalog["_text"][key] != key, f"{locale} leaves {key!r} in English"


def test_non_english_catalogs_translate_common_ui_status_strings():
    config = Config()
    keys = {
        "AI Behavior",
        "Audio Input Device",
        "Audio Output Device",
        "Audio capture ready",
        "Choose the language used for PolyTalk controls and messages.",
        "Connecting to server",
        "Connection issue detected. Please try again.",
        "Failed to start microphone. Please check permissions.",
        "Failed to start tab audio capture",
        "Interface Language",
        "Languages swapped!",
        "Listening...",
        'No audio track found. Please select a tab with audio and enable "Share audio".',
        "Opening screen sharing dialog",
        "Paused. Audio transmission stopped.",
        "PolyTalk • Privacy-first Real-time Translation",
        "Ready to use microphone for live translation",
        "Ready. Listening now.",
        "Recording",
        "Resumed. Audio transmission continues.",
        "Server connected",
        "Settings saved successfully!",
        "Translated Voice Output",
        "Translation Instructions",
        "Translate formally. Keep technical terms in English.",
        "Optional guidance sent with live, conversation, and tab-audio translation sessions.",
        "User cancelled screen sharing",
        "Your browser does not support audio recording. Please use a modern browser like Chrome, Firefox, or Edge.",
        "Your browser does not support tab audio sharing.",
        "Your browser does not support the audio element.",
        "getUserMedia is not supported in this browser.",
    }

    for locale in set(SUPPORTED_UI_LOCALE_CODES) - {"en"}:
        catalog = public_catalog(locale, config)
        for key in keys:
            assert catalog["_text"][key] != key, f"{locale} leaves {key!r} in English"
        assert not catalog["js.failed_share_tab_audio"].startswith("Failed to share")
        assert not catalog["js.output_device_changed"].startswith("Output device")
        assert not catalog["js.speaker_number"].startswith("Speaker ")


def test_locale_catalogs_have_required_shape():
    required = set(SUPPORTED_UI_LOCALE_CODES)
    locale_dir = Path("app/locales")
    catalogs = {path.stem for path in locale_dir.glob("*.json")}

    assert required.issubset(catalogs)
    assert (catalogs - {"template"}).issubset(required)

    for path in locale_dir.glob("*.json"):
        if path.stem == "template":
            continue
        data = json.loads(path.read_text())
        assert "app.title" in data
        assert isinstance(data.get("_text"), dict)
        assert isinstance(data.get("_languages"), dict)
        assert set(data["_languages"]) >= {"en", "de", "es", "fr"}


def test_frontend_i18n_hooks_are_present():
    i18n_source = Path("app/static/js/i18n.js").read_text()
    app_source = Path("app/static/js/polytalk-app.js").read_text()
    audio_source = Path("app/static/js/audio-recorder.js").read_text()

    assert "window.PolyTalkI18n" in i18n_source
    assert "initLocaleSwitchers" in i18n_source
    assert "translateLanguageOptions" in i18n_source
    assert "hasOwn(messages, key)" in i18n_source
    assert "hasOwn(exactMap, raw)" in i18n_source
    assert "this.uiText(" in app_source
    assert "this.t(" in app_source
    assert "this.uiText(" in audio_source
