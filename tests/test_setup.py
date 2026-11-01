"""Setup diagnostics: honest-but-safe failure messages and the startup preflight."""
import socket

import pytest
from playwright.sync_api import Error as PWError
from playwright.sync_api import TimeoutError as PWTimeout

from core import automation, preflight
from portal import server

PROFILE = {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
           "college": "Riverdale Institute of Technology", "course": "B.Tech Computer Science",
           "academic_year": "3", "family_income": "350000", "cgpa": "8.4"}


def _errors(exc, values=None):
    return automation._failure({"errors": []}, exc, values)["errors"]


def test_missing_browser_shows_type_first_line_and_fix():
    exc = PWError("BrowserType.launch: Executable doesn't exist at /Users/priya/Library/Caches/ms-playwright/"
                  "chromium_headless_shell-1243/chrome-headless-shell\n╔════╗\n║ Looks like Playwright ...")
    [msg] = _errors(exc)
    assert "Error: BrowserType.launch: Executable doesn't exist" in msg
    assert "python3 -m playwright install chromium" in msg
    assert "priya" not in msg and "~/Library/Caches" in msg      # local username removed
    assert "╔" not in msg and "Looks like" not in msg              # only the first line


def test_detail_redacts_values_keys_emails_and_query(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRET1234567890")
    exc = PWError("Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765/svc/scholarship/?key=abc123 "
                  "while typing Aarav Sharma aarav.sharma@example.edu sk-ant-SECRET1234567890 AIzaSyA1234567890abcdefghij")
    [msg] = _errors(exc, PROFILE)
    for leaked in ("Aarav Sharma", "aarav.sharma@example.edu", "SECRET", "AIzaSy", "abc123"):
        assert leaked not in msg
    assert "ERR_CONNECTION_REFUSED" in msg and "mock portal is not answering" in msg


def test_timeout_message_does_not_claim_nothing_was_submitted():
    [msg] = _errors(PWTimeout("Page.goto: Timeout 8000ms exceeded.\nCall log: ..."))
    assert "TimeoutError: Page.goto: Timeout 8000ms exceeded." in msg
    assert "Nothing was submitted" not in msg and "Call log" not in msg


def test_unknown_error_still_reports_type_and_points_to_doctor():
    [msg] = _errors(OSError("something odd"))
    assert "OSError: something odd" in msg and "scripts/doctor.py" in msg


def test_portal_down_message_is_specific():
    with socket.socket() as s:          # a free port nobody listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    res = automation.fill_form("scholarship", PROFILE, "k-down", f"http://127.0.0.1:{port}/")
    assert not res["ok"]
    msg = res["errors"][-1]
    assert "ERR_CONNECTION_REFUSED" in msg and "Aarav" not in msg


def test_missing_chromium_reported_by_preflight(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    c = preflight.check_chromium()
    assert not c["ok"]
    assert "Executable doesn't exist" in c["detail"]
    assert "playwright install chromium" in c["fix"]


def test_chromium_preflight_passes_when_installed():
    assert preflight.check_chromium()["ok"]


def test_port_taken_by_other_program_is_detected(monkeypatch):
    import config
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        monkeypatch.setattr(config, "PORTAL_PORT", port)
        monkeypatch.setattr(config, "PORTAL_URL", f"http://127.0.0.1:{port}/")
        assert not server.is_up(port)
        with pytest.raises(OSError):
            server.ensure_running()
        c = preflight.check_portal()
        assert not c["ok"] and "PORTAL_PORT" in c["fix"]


def test_portal_health_identifies_our_portal(portal_url):
    port = int(portal_url.rstrip("/").rsplit(":", 1)[1])
    assert server.is_up(port)
    assert preflight.portal_health(port) == {"reachable": True, "ours": True}
