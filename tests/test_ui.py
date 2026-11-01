from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _click(at, label):
    next(b for b in at.button if b.label == label).click().run(timeout=90)


@pytest.mark.parametrize("demo,prefix", [("Demo: scholarship", "SCH-"), ("Demo: licence renewal", "DLR-")])
def test_full_ui_journey(demo, prefix):
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert not at.exception
    _click(at, demo)
    _click(at, "Analyze request")
    _click(at, "Authorize agent to prepare the form")
    _click(at, "Continue to approval")
    at.checkbox(key="confirm").check().run()
    _click(at, "Submit application")
    assert not at.exception
    assert any(prefix in m.value for m in at.metric)


def test_language_toggle_switches_ui_strings():
    at = AppTest.from_file(APP, default_timeout=90).run()
    lang = next(s for s in at.sidebar.selectbox if s.key == "lang")
    assert lang.value == "en"
    lang.set_value("hi").run(timeout=90)
    assert not at.exception
    assert any("बताइए आपको क्या चाहिए" in h.value for h in at.header)
    assert any("अनुरोध समझें" in b.label for b in at.button)


def test_hinglish_toggle_switches_ui_strings():
    at = AppTest.from_file(APP, default_timeout=90).run()
    lang = next(s for s in at.sidebar.selectbox if s.key == "lang")
    lang.set_value("hinglish").run(timeout=90)
    assert not at.exception
    assert any("Bataiye aapko kya service chahiye" in h.value for h in at.header)
    assert any("Naye sire se shuru karein" == b.label for b in at.sidebar.button)
    assert any("Demo: scholarship" == b.label for b in at.button)


def test_demo_subsidy_button_appears():
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert any(b.label == "Demo: LPG subsidy" for b in at.button)


def test_audit_report_button_after_preparation():
    at = AppTest.from_file(APP, default_timeout=120).run()
    _click(at, "Demo: scholarship")
    _click(at, "Analyze request")
    _click(at, "Authorize agent to prepare the form")
    # at.get() works on every Streamlit version; at.download_button only exists in newer ones.
    labels = [getattr(b, "label", None) or b.proto.label for b in at.get("download_button")]
    assert "Download audit report (HTML)" in labels


def test_missing_field_blocks_preparation():
    at = AppTest.from_file(APP, default_timeout=90).run()
    _click(at, "Demo: licence (missing PIN code)")
    _click(at, "Analyze request")
    assert not any(b.label == "Authorize agent to prepare the form" for b in at.button)
    assert any("PIN code" in w.value for w in at.warning)


def test_chat_panel_completes_missing_field_journey():
    at = AppTest.from_file(APP, default_timeout=120).run()
    _click(at, "Demo: scholarship (missing income)")
    _click(at, "Analyze request")
    assert len(at.chat_input) == 1
    at.chat_input[0].set_value("our annual family income is 3.5 lakh").run(timeout=90)
    assert not at.exception
    assert any("Authorize agent to prepare the form" in b.label for b in at.button)
    _click(at, "Authorize agent to prepare the form")
    _click(at, "Continue to approval")
    at.checkbox(key="confirm").check().run()
    _click(at, "Submit application")
    assert not at.exception
    assert any("SCH-" in m.value for m in at.metric)


def test_missing_browser_shows_setup_error_and_blocks_preparation(monkeypatch, tmp_path):
    import streamlit as st
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))   # no Chromium here
    st.cache_resource.clear()
    try:
        at = AppTest.from_file(APP, default_timeout=90).run()
        assert not at.exception
        assert any("Setup problem: Playwright Chromium" in e.value and "playwright install chromium" in e.value
                   for e in at.error)
        _click(at, "Demo: scholarship")
        _click(at, "Analyze request")
        prepare = next(b for b in at.button if b.label == "Authorize agent to prepare the form")
        assert prepare.disabled
    finally:
        st.cache_resource.clear()


def test_chat_answer_reaches_profile_and_survives_save():
    """Regression: a value given in chat must appear in the profile box, so "Save & re-validate" keeps it."""
    at = AppTest.from_file(APP, default_timeout=90).run()
    _click(at, "Demo: scholarship (missing income)")
    _click(at, "Analyze request")
    at.chat_input[0].set_value("family income is 3.5 lakh").run(timeout=90)
    assert at.session_state["in_family_income"] == "3.5 lakh"
    _click(at, "Save & re-validate")
    assert not at.exception
    assert any("present and valid" in s.value for s in at.success)
