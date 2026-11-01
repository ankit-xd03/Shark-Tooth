"""Optional live-LLM integration tests (P3-M): auto-skipped unless a real API key is configured.

These tests make real network calls to the configured provider. They verify routing, extraction and
planning against live models; the model identifiers in config.py were verified against the provider
docs (claude-haiku-5-5, claude-sonnet-5-5, gemini-2.5-flash) before being used as defaults.
"""
import os

import pytest

import config
from core import automation, extractor, planner, schema
from tests.conftest import PROFILES


def _key_configured() -> bool:
    """True when an LLM key is set, even if DEMO_MODE=true is in .env for the demo."""
    saved = os.environ.pop("DEMO_MODE", None)
    try:
        return config.llm_available()
    finally:
        if saved is not None:
            os.environ["DEMO_MODE"] = saved


pytestmark = pytest.mark.skipif(not _key_configured(),
                                reason="no LLM key configured; live LLM tests are skipped")


@pytest.fixture(autouse=True)
def live_llm_mode(monkeypatch):
    # conftest.py forces DEMO_MODE=true for every test; these tests must really call the LLM.
    monkeypatch.setenv("DEMO_MODE", "false")


def test_live_extraction_returns_stated_fields_only():
    text = ("I am Aarav Sharma, a second-year B.Sc Physics student at Riverdale Institute of Technology. "
            "My family income is 4.2 lakh and my CGPA is 9.1.")
    fields, mode, _ = extractor.extract(text, "scholarship")
    assert mode == "llm"
    assert fields.get("cgpa") == "9.1" and fields.get("family_income")
    assert all(k in schema.get("scholarship").names for k in fields)


def test_live_routing_classifies_service():
    sid = extractor.classify_service("I need money support for my engineering studies at college")
    assert sid in (None, "scholarship")
    sid2 = extractor.classify_service("My two wheeler licence has expired, please renew it")
    assert sid2 in (None, "licence")


def test_live_planning_on_real_portal_page(portal_url):
    with automation._browser(portal_url) as (page, violations):
        page.goto(f"{portal_url}svc/scholarship/step/1?key=live-llm-plan")
        snap = automation.snapshot(page)
    plan = planner.plan(snap, ["full_name", "email"], schema.get("scholarship").labels)
    assert plan["mode"] == "llm"
    assert {f for f, _ in plan["fills"]} <= {"full_name", "email"}
    assert len(plan["fills"]) == 2
