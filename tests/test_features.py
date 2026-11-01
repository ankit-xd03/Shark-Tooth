"""Feature tests: chat (P1-B), randomized portal (P1-C), self-healing (P2-F), tracking (P1-D),
eligibility pre-check (P2-G), OTP pause (P2-H), subsidy (P2-I), Hindi (P2-J), documents (P2-E)."""
import json
import urllib.request
from pathlib import Path

import pytest

from core import automation, schema, store
from core.controller import Controller
from portal import server
from tests.conftest import PROFILES, REQUESTS
from tests.test_flow import values


def test_portal_track_api_progresses(portal_url, monkeypatch):
    monkeypatch.setenv("PORTAL_TRACK_DELAY_SECONDS", "0")
    automation.submit_application("licence", values("licence"), "k-track", portal_url)
    rec = automation.portal_status("k-track", portal_url)["record"]
    ref = rec["application_id"]
    with urllib.request.urlopen(f"{portal_url}api/track?ref={ref}") as r:
        data = json.loads(r.read())
    assert data["found"] and data["application_status"] == "APPROVED"


def test_portal_track_api_unknown_ref(portal_url):
    with urllib.request.urlopen(f"{portal_url}api/track?ref=NOPE-1-XXXX") as r:
        data = json.loads(r.read())
    assert data["found"] is False and data["application_status"] is None


def test_track_application_reads_status_via_browser(portal_url, monkeypatch):
    monkeypatch.setenv("PORTAL_TRACK_DELAY_SECONDS", "0")
    out = automation.submit_application("scholarship", values("scholarship"), "k-track2", portal_url)
    ref = out["receipt"]["application_id"]
    res = automation.track_application(ref, portal_url)
    assert res["found"] and res["ref"] == ref and res["status"] == "APPROVED"


def test_track_application_rejects_mismatched_ref(portal_url):
    assert automation.track_application("SCH-2099-ZZZZZZZZ", portal_url)["found"] is False


def test_refresh_tracking_updates_history(ready, monkeypatch):
    monkeypatch.setenv("PORTAL_TRACK_DELAY_SECONDS", "0")
    c = ready()
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    ref = c.receipt["application_id"]
    c.refresh_tracking()
    assert c.tracking and c.tracking["status"] == "APPROVED" and c.tracking["ref"] == ref
    assert store.history()[0]["status"] == "APPROVED"
    c2 = Controller(automation=c.automation)
    c2.refresh_tracking()
    assert "no application ID" in c2.message


def test_track_page_never_shows_record_without_ref(portal_url):
    with urllib.request.urlopen(f"{portal_url}track") as r:
        body = r.read().decode()
    assert "No application found" in body


def test_read_eligibility_all_services(portal_url):
    assert automation.read_eligibility("scholarship", portal_url) == {"income_max": 800000, "min_cgpa": 6.0}
    assert automation.read_eligibility("licence", portal_url) == {"grace_days": 365}
    assert automation.read_eligibility("subsidy", portal_url) == {"income_max": 250000, "connection": "PMUY"}


def test_eligibility_precheck_warns_but_allows(ready):
    c = ready(family_income="900000")
    c.prepare()
    assert c.auto["ok"] and c.eligibility_risks
    assert "exceeds the portal limit" in c.eligibility_risks[0]
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome == "rejected"


def test_eligibility_precheck_silent_when_safe(ready):
    c = ready()
    c.prepare()
    assert c.auto["ok"] and c.eligibility_risks == []


def test_eligibility_survives_missing_page(make_controller, monkeypatch):
    def boom(sid):
        raise RuntimeError("portal down")
    c = make_controller()
    monkeypatch.setattr(c.automation, "read_eligibility", boom)
    c.analyze(REQUESTS["scholarship"], PROFILES["scholarship"], "scholarship")
    c.prepare()
    assert c.stage == 3 and c.eligibility_risks == []


def test_subsidy_validation_rules():
    svc = schema.get("subsidy")
    clean, errors, missing = svc.validate(PROFILES["subsidy"])
    assert not errors and not missing and clean["connection_type"] == "PMUY"
    _, errors, _ = svc.validate({**PROFILES["subsidy"], "bank_ifsc": "SBIN1234",
                                 "consumer_no": "12345", "connection_type": "Car"})
    assert set(errors) == {"bank_ifsc", "consumer_no", "connection_type"}


def test_subsidy_end_to_end_rejects_general_connection(ready):
    c = ready("subsidy", connection_type="GENERAL")
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome == "rejected" and "PMUY" in c.message


def test_subsidy_end_to_end_accepted(ready):
    c = ready("subsidy")
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome == "accepted" and c.receipt["application_id"].startswith("LPG-")


def test_otp_pause_hands_control_to_user(ready, portal_url, monkeypatch):
    monkeypatch.setenv("PORTAL_OTP", "true")
    c = ready()
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome is None and c.otp_pending and c.stage == 4 and c.receipt is None
    assert not automation.portal_status(c.idem_key, portal_url)["found"]
    code = server._session(c.idem_key)["otp"]
    page = urllib.request.urlopen(f"{portal_url}svc/scholarship/otp?key={c.idem_key}").read().decode()
    assert code not in page
    sms = urllib.request.urlopen(f"{portal_url}sms?key={c.idem_key}").read().decode()
    assert code in sms and "Never share" in sms
    assert all(str(code) not in e for e in c.events)
    c.submit_otp("12ab78")
    assert c.otp_pending and "6-digit" in c.message
    c.submit_otp("000000")
    assert c.otp_pending and "rejected" in c.message.lower()
    c.submit_otp(code)
    assert c.outcome == "accepted" and c.stage == 5 and not c.otp_pending
    assert c.receipt["application_id"].startswith("SCH-")
    with pytest.raises(RuntimeError):
        c.submit_otp(code)


def test_otp_submit_blocked_without_pause(ready):
    with pytest.raises(RuntimeError):
        ready().submit_otp("123456")


def test_otp_complete_automation_direct(portal_url, monkeypatch):
    monkeypatch.setenv("PORTAL_OTP", "true")
    out = automation.submit_application("licence", values("licence"), "k-otp-direct", portal_url)
    assert out["outcome"] == "otp_required" and out["receipt"] is None
    code = server._session("k-otp-direct")["otp"]
    done = automation.complete_otp("licence", code, "k-otp-direct", portal_url)
    assert done["outcome"] == "accepted" and done["receipt"]["application_id"].startswith("DLR-")
    again = automation.submit_application("licence", values("licence"), "k-otp-direct", portal_url)
    assert again["outcome"] == "accepted" and again["receipt"]["application_id"] == done["receipt"]["application_id"]


def test_hinglish_request_extracts_and_routes():
    from core import extractor
    text = "Mujhe scholarship ke liye apply karna hai, income 3.5 lakh hai, CGPA 8.4"
    assert schema.detect_service(text) == "scholarship"
    out = extractor.demo_extract(text, "scholarship")
    assert out["family_income"] == "3.5 lakh" and out["cgpa"] == "8.4"


def test_devanagari_request_extracts_and_routes():
    from core import extractor
    text = "मुझे छात्रवृत्ति चाहिए। आय ३.५ लाख है, CGPA ८.४, मेरा नाम आरव शर्मा है"
    assert schema.detect_service(text) == "scholarship"
    out = extractor.demo_extract(text, "scholarship")
    assert out["family_income"] == "3.5 lakh" and out["cgpa"] == "8.4" and out["full_name"] == "आरव शर्मा"


def test_hindi_licence_routing():
    assert schema.detect_service("मुझे ड्राइविंग लाइसेंस नवीनीकरण करवाना है") == "licence"
    assert schema.detect_service("LPG सब्सिडी का दावा करना है") == "subsidy"


def test_income_parsing_hindi_and_devanagari_digits():
    assert schema.parse_income("३.५ लाख") == 350000
    assert schema.parse_income("₹३,५०,०००") == 350000
    assert schema.parse_income("2 लाख") == 200000


def test_hindi_ordinals_and_validators():
    from core import extractor
    out = extractor.demo_extract("मैं तीसरे साल में पढ़ता हूँ", "scholarship")
    assert out["academic_year"] == "3"
    assert schema.get("scholarship").validate({**PROFILES["scholarship"], "academic_year": "३"})[0]["academic_year"] == 3


def test_hindi_values_pass_validators_end_to_end(ready):
    c = ready("scholarship", full_name="आरव शर्मा")
    assert c.is_valid and c.clean["full_name"] == "आरव शर्मा"


SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_sample_marksheet_pdf_fills_scholarship(make_controller):
    c = make_controller()
    out = c.ingest_document("marksheet_sample.pdf", (SAMPLES / "marksheet_sample.pdf").read_bytes())
    assert out["service"] == "scholarship"
    assert set(out["filled"]) >= {"full_name", "college", "academic_year", "cgpa"}
    assert c.sources["cgpa"] == "marksheet_sample.pdf" and c.stage >= 1


def test_sample_income_certificate_fills_income(make_controller):
    c = make_controller()
    c.analyze(REQUESTS["scholarship"], PROFILES["scholarship"], "scholarship")
    c.fields["family_income"] = ""
    out = c.ingest_document("income_certificate_sample.pdf",
                            (SAMPLES / "income_certificate_sample.pdf").read_bytes())
    assert "family_income" in out["filled"] and c.clean["family_income"] == 350000


def test_sample_licence_copy_fills_licence(make_controller):
    c = make_controller()
    out = c.ingest_document("licence_copy_sample.pdf", (SAMPLES / "licence_copy_sample.pdf").read_bytes())
    assert out["service"] == "licence" and "license_number" in out["filled"]


def test_image_without_llm_key_is_rejected(make_controller, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    c = make_controller()
    with pytest.raises(ValueError) as e:
        c.ingest_document("scan.png", b"\x89PNG-not-really")
    assert "vision" in str(e.value).lower()


def test_unsupported_document_type(make_controller):
    with pytest.raises(ValueError):
        make_controller().ingest_document("notes.txt", b"hello")


def test_document_service_mismatch_is_reported(make_controller):
    c = make_controller()
    c.analyze(REQUESTS["licence"], PROFILES["licence"], "licence")
    out = c.ingest_document("marksheet_sample.pdf", (SAMPLES / "marksheet_sample.pdf").read_bytes())
    assert "looks like a" in out["warning"] and out["filled"] == ["full_name"]


def test_chat_question_targets_first_missing_field(ready):
    c = ready(family_income="")
    q = c.chat_question()
    assert q["field"] == "family_income" and "income" in q["question"].lower()


def test_chat_question_none_when_valid(ready):
    assert ready().chat_question() is None


def test_chat_reply_fills_missing_income(ready):
    c = ready(family_income="")
    reply = c.chat_reply("our annual family income is 3.5 lakh")
    assert c.fields["family_income"] == "3.5 lakh"
    assert c.sources["family_income"] == "chat"
    assert c.is_valid and "authorize" in reply.lower()


def test_chat_reply_invalid_value_is_not_guessed(ready):
    c = ready(family_income="")
    c.chat_reply("honestly I am not sure, maybe normal amount")
    assert c.fields["family_income"] == "" and not c.is_valid


def test_chat_reply_cannot_contaminate_other_fields(ready):
    c = ready()
    c.fields["cgpa"] = ""
    c.errors, c.missing = {}, ["cgpa"]
    c.chat_reply("cgpa is 9.1 and my income was fine")
    assert c.fields["cgpa"] == "9.1"


def test_multi_value_reply_fills_both(ready):
    c = ready(family_income="")
    c.fields["cgpa"] = ""
    c.missing = ["family_income", "cgpa"]
    c.errors = {}
    c.chat_reply("income is 4.2 lakh and cgpa is 7.9")
    assert c.fields["family_income"] == "4.2 lakh" and c.fields["cgpa"] == "7.9" and c.is_valid


def test_chat_only_journey_end_to_end(make_controller):
    c = make_controller()
    c.analyze(REQUESTS["scholarship"], {k: v for k, v in PROFILES["scholarship"].items()
                                        if k != "family_income"}, "scholarship")
    assert c.missing == ["family_income"]
    c.chat_reply("family income 350000 per year")
    assert c.is_valid
    c.prepare()
    c.proceed_to_approval()
    c.submit(confirmed=True)
    assert c.outcome == "accepted" and c.receipt["application_id"].startswith("SCH-")


def test_chat_blocked_before_analyze(make_controller):
    with pytest.raises(RuntimeError):
        make_controller().chat_reply("income 3 lakh")


SEED_SET = [2, 9, 14]


@pytest.mark.parametrize("sid", ["scholarship", "licence", "subsidy"])
@pytest.mark.parametrize("seed", SEED_SET)
def test_randomized_portal_layout_fixed_seed_set(portal_url, sid, seed):
    from tests.conftest import PROFILES as P
    svc = schema.get(sid)
    vals = svc.form_values(svc.validate(P[sid])[0])
    res = automation.fill_form(sid, vals, f"bench-{seed}-{sid}", portal_url)
    assert res["ok"], f"seed {seed}/{sid}: {res['errors']}"


def test_portal_layout_deterministic_per_key():
    a = server.layout_for("licence", "bench-7-x")
    b = server.layout_for("licence", "bench-7-x")
    assert a is b or a == b
    c = server.layout_for("licence", "bench-8-x")
    assert a["id_sfx"] != c["id_sfx"] or a["buttons"] != c["buttons"] or a["labels"] != c["labels"]


def test_unseeded_portal_uses_canonical_layout():
    assert server.layout_for("licence", "k-canonical") is server._canonical_layout("licence")


def test_self_healing_hyphen_date_portal(portal_url, monkeypatch):
    seed = next(s for s in range(1, 30)
                if server.layout_for("licence", f"bench-{s}-licence")["date_hyphen"])
    monkeypatch.setenv("PORTAL_DATE_HYPHENS", "")
    res = automation.fill_form("licence", values("licence"), f"bench-{seed}-licence", portal_url)
    assert res["ok"], res["errors"]
    assert any("format correction" in (r.get("note") or "") for r in res["trace"])
    assert any(c["field"] in ("date_of_birth", "expiry_date") for c in res["corrections"])


def test_self_healing_accepts_same_source_value_only(portal_url, monkeypatch):
    monkeypatch.setenv("PORTAL_DATE_HYPHENS", "true")
    res = automation.fill_form("licence", values("licence"), "k-hyphen-env", portal_url)
    assert res["ok"] and res["corrections"]
    day, month, year = values("licence")["date_of_birth"].split("/")
    assert all(c["field"] in ("date_of_birth", "expiry_date") for c in res["corrections"])
    assert f"{day}-{month}-{year}"
