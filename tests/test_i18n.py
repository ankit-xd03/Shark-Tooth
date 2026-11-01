"""Tests for the trilingual i18n module (core/i18n.py) and its UI integration."""
from string import Formatter

from core.controller import STAGES
from core.i18n import LANGUAGES, STAGE_NAMES, TRANSLATIONS, stages, t


def _placeholders(text: str) -> set:
    return {f for _, f, _, _ in Formatter().parse(text) if f is not None}


def test_every_key_translated_in_every_language():
    for key, entry in TRANSLATIONS.items():
        for code in LANGUAGES:
            assert entry.get(code), f"key '{key}' missing translation for '{code}'"
            assert entry[code].strip(), f"key '{key}' has an empty '{code}' translation"


def test_placeholders_match_across_languages():
    for key, entry in TRANSLATIONS.items():
        expected = _placeholders(entry["en"])
        for code in ("hi", "hinglish"):
            assert _placeholders(entry[code]) == expected, \
                f"key '{key}' placeholder mismatch in '{code}'"


def test_t_falls_back_for_missing_language_and_missing_key():
    assert t("submit", "hi") == "आवेदन जमा करें"
    assert t("submit", "xx") == "Submit application"
    assert t("nonexistent_key", "hi") == "nonexistent_key"


def test_formatting_placeholders():
    assert t("stage_progress", "en", n=2) == "Stage 2 of 5"
    assert t("stage_progress", "hi", n=2) == "चरण 2 / 5"
    assert t("missing_warn", "en", field="PIN code").startswith("**PIN code** is required")


def test_stages_match_controller_and_language_count():
    assert stages("en") == STAGES
    for code in LANGUAGES:
        assert len(stages(code)) == len(STAGES) == 5
        assert STAGE_NAMES[code] == stages(code)
