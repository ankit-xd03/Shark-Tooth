import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core import automation, schema, store
from tests.conftest import PROFILES


def values(sid, **o):
    svc = schema.get(sid)
    return svc.form_values(svc.validate({**PROFILES[sid], **o})[0])


@pytest.mark.parametrize("sid", ["scholarship", "licence"])
def test_fill_form_completes_all_fields_through_obstacles(portal_url, sid):
    res = automation.fill_form(sid, values(sid), f"k-fill-{sid}", portal_url)
    assert res["ok"] and not res["outstanding"] and sorted(res["completed"]) == sorted(schema.get(sid).names)
    pages = [r["page"] for r in res["trace"]]
    assert pages.count("obstacle") == 2 and {"landing", "form", "review"} <= set(pages)
    assert all("click" not in r["action"] or "Final" not in r["action"] for r in res["trace"])


def test_trace_includes_screenshot_per_step(portal_url):
    res = automation.fill_form("scholarship", values("scholarship"), "k-shots", portal_url)
    assert res["ok"] and len(res["shots"]) == len(res["trace"])
    assert all(s[:2] == b"\xff\xd8" and len(s) > 1000 for s in res["shots"])
    pages = [r["page"] for r in res["trace"]]
    assert "obstacle" in pages


def test_trace_includes_screenshot_of_submit_result(portal_url):
    out = automation.submit_application("licence", values("licence"), "k-shots-sub", portal_url)
    assert out["outcome"] == "accepted"
    assert out["fill"]["shots"] and out["fill"]["shots"][-1][:2] == b"\xff\xd8"


def test_cannot_prepare_with_missing_fields(ready):
    c = ready(family_income="")
    assert c.stage == 1 and c.missing == ["family_income"]
    with pytest.raises(RuntimeError):
        c.prepare()


def test_unsupported_service(make_controller):
    c = make_controller()
    c.analyze("Help me renew my passport", {}, "scholarship")
    assert c.stage == 0 and "Unsupported" in c.message


def test_request_overrides_selected_service(make_controller):
    c = make_controller()
    c.analyze("Please renew my driving licence", {}, "scholarship")
    assert c.service.id == "licence"


def test_portal_down_stops_safely():
    res = automation.fill_form("scholarship", values("scholarship"), "k-down", "http://127.0.0.1:1/")
    assert not res["ok"] and res["errors"]


class _Blank(BaseHTTPRequestHandler):
    body = b"<html><title>Nothing here</title><body><p>No forms.</p></body></html>"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *a):
        pass


def _serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


def test_missing_elements_stop_instead_of_guessing():
    srv, base = _serve(_Blank)
    res = automation.fill_form("scholarship", values("scholarship"), "k-blank", base)
    srv.shutdown()
    assert not res["ok"] and "stopped instead of guessing" in res["errors"][-1] and not res["completed"]


def test_redirect_off_origin_is_blocked():
    class Away(_Blank):
        body = b"<html><head><script>location.href='http://203.0.113.9/'</script></head><body>x</body></html>"

    srv, base = _serve(Away)
    res = automation.fill_form("scholarship", values("scholarship"), "k-away", base)
    srv.shutdown()
    assert not res["ok"] and not res["completed"]


def test_no_submit_before_approval_stage(ready):
    with pytest.raises(RuntimeError):
        ready().submit(confirmed=True)


def test_submission_requires_explicit_approval(ready):
    c = ready()
    c.prepare()
    c.proceed_to_approval()
    with pytest.raises(PermissionError):
        c.submit(confirmed=False)
    assert c.receipt is None


@pytest.mark.parametrize("sid,prefix", [("scholarship", "SCH-"), ("licence", "DLR-")])
def test_end_to_end_submit_and_receipt(ready, sid, prefix):
    c = ready(sid)
    c.prepare()
    assert c.stage == 3 and c.auto["ok"]
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.stage == 5 and c.outcome == "accepted"
    assert c.receipt["application_id"].startswith(prefix) and c.receipt["raw"]["status"] == "ACCEPTED"
    assert store.history()[0]["application_id"] == c.receipt["application_id"]
    with pytest.raises(RuntimeError):
        c.submit(confirmed=True)


@pytest.mark.parametrize("sid,override,word", [("scholarship", {"family_income": "900000"}, "income"),
                                               ("scholarship", {"cgpa": "5.2"}, "cgpa"),
                                               ("licence", {"expiry_date": "01/01/2024"}, "expired")])
def test_portal_rejection_has_no_receipt(ready, sid, override, word):
    c = ready(sid, **override)
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome == "rejected" and c.receipt is None and c.stage == 4
    assert word in c.message.lower()


def test_duplicate_key_is_idempotent(portal_url):
    v = values("licence")
    a = automation.submit_application("licence", v, "k-dup", portal_url)
    b = automation.submit_application("licence", v, "k-dup", portal_url)
    assert a["receipt"]["application_id"] == b["receipt"]["application_id"]
    assert automation.portal_status("k-dup", portal_url)["found"]


def test_portal_validation_error_is_reported_per_field(portal_url):
    bad = values("scholarship")
    bad["email"] = "not-an-email"
    res = automation.fill_form("scholarship", bad, "k-bad", portal_url)
    assert not res["ok"] and "email" in res["field_errors"] and "email" in res["outstanding"]


def test_uncertain_result_is_checked_not_retried(ready, monkeypatch):
    c = ready()
    c.prepare()
    c.proceed_to_approval()
    monkeypatch.setattr(c.automation, "submit_application",
                        lambda *a: {"outcome": "uncertain", "message": "unknown", "receipt": None, "fill": None})
    c.submit(confirmed=True)
    assert c.outcome == "uncertain"
    with pytest.raises(RuntimeError):
        c.submit(confirmed=True)
    c.check_status()
    assert c.outcome == "error" and "safe to try again" in c.message
