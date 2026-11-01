import socket
from types import SimpleNamespace

import pytest

from core import automation
from core.controller import Controller
from portal import server

PROFILES = {
    "scholarship": {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
                    "college": "Riverdale Institute of Technology", "course": "B.Tech Computer Science",
                    "academic_year": "3", "family_income": "350000", "cgpa": "8.4"},
    "licence": {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
                "date_of_birth": "12/05/2001", "license_number": "AS0120200012345",
                "expiry_date": "15/12/2026", "vehicle_class": "LMV", "pincode": "781001"},
    "subsidy": {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
                "consumer_no": "5500012345", "connection_type": "PMUY", "bank_ifsc": "SBIN0001234",
                "account_last4": "4821", "annual_income": "180000"},
}
REQUESTS = {"scholarship": "Help me apply for the merit scholarship.",
            "licence": "Please renew my driving licence.",
            "subsidy": "I want to claim the LPG connection subsidy for my Ujjwala connection."}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("CIVICPILOT_DB", str(tmp_path / "test.db"))


@pytest.fixture(scope="session")
def portal_url():
    port = _free_port()
    srv = server.start_in_thread(port)
    yield f"http://127.0.0.1:{port}/"
    srv.shutdown()


@pytest.fixture
def make_controller(portal_url):
    def build(base=None):
        base = base or portal_url
        auto = SimpleNamespace(
            fill_form=lambda sid, v, k: automation.fill_form(sid, v, k, base),
            submit_application=lambda sid, v, k: automation.submit_application(sid, v, k, base),
            portal_status=lambda k: automation.portal_status(k, base),
            track_application=lambda ref: automation.track_application(ref, base),
            read_eligibility=lambda sid: automation.read_eligibility(sid, base),
            complete_otp=lambda sid, code, k: automation.complete_otp(sid, code, k, base))
        return Controller(automation=auto)
    return build


@pytest.fixture
def ready(make_controller):
    def build(sid="scholarship", **overrides):
        c = make_controller()
        c.analyze(REQUESTS[sid], {**PROFILES[sid], **overrides}, sid)
        return c
    return build
