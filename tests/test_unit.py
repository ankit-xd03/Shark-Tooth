import pytest

from core import extractor, planner, schema
from core.automation import choose_option, is_allowed_url
from tests.conftest import PROFILES


def test_missing_field_not_invented():
    svc = schema.get("scholarship")
    clean, errors, missing = svc.validate({**PROFILES["scholarship"], "family_income": ""})
    assert missing == ["family_income"] and "family_income" not in clean and not errors


def test_invalid_input_scholarship():
    _, errors, _ = schema.get("scholarship").validate(
        {**PROFILES["scholarship"], "cgpa": "11", "email": "bad", "academic_year": "9"})
    assert set(errors) == {"cgpa", "email", "academic_year"}


def test_invalid_input_licence():
    _, errors, _ = schema.get("licence").validate(
        {**PROFILES["licence"], "license_number": "123", "date_of_birth": "01/01/2015",
         "vehicle_class": "tractor", "pincode": "12"})
    assert set(errors) == {"license_number", "date_of_birth", "vehicle_class", "pincode"}


@pytest.mark.parametrize("raw,val", [("3.5 lakh", 350000), ("Rs. 3,50,000", 350000), ("350000", 350000)])
def test_income_parsing(raw, val):
    assert schema.parse_income(raw) == val


def test_routing_and_unsupported():
    assert schema.detect_service("I need a scholarship") == "scholarship"
    assert schema.detect_service("renew my driving licence") == "licence"
    assert schema.detect_service("Help me renew my passport") is None
    assert extractor.classify_service("Help me renew my passport") is None


def test_demo_extract_does_not_invent():
    assert extractor.demo_extract("I'm a third-year student, CGPA 8.4") == {"academic_year": "3", "cgpa": "8.4"}


def test_licence_extraction():
    out = extractor.demo_extract(
        "I am Aarav Sharma, licence AS01 2020 0012345, DOB 12/05/2001, it expires on 15/12/2026, "
        "class LMV, PIN code 781001", "licence")
    assert out["license_number"].replace(" ", "") == "AS0120200012345"
    assert out["date_of_birth"] == "12/05/2001" and out["expiry_date"] == "15/12/2026"
    assert out["vehicle_class"] == "LMV" and out["pincode"] == "781001" and out["full_name"] == "Aarav Sharma"


def test_unexpected_url_blocked():
    base = "http://127.0.0.1:8765/"
    assert is_allowed_url("http://127.0.0.1:8765/svc/licence/", base) and is_allowed_url("about:blank", base)
    assert not is_allowed_url("https://evil.example.com/", base)
    assert not is_allowed_url("http://127.0.0.1:9999/", base)


def test_choose_option_handles_coded_dropdowns():
    years = [{"value": "", "text": "-- Select --"}, {"value": "Y3", "text": "3rd Year"}]
    cls = [{"value": "C01", "text": "LMV - Light Motor Vehicle (Car)"}, {"value": "C02", "text": "MCWG - Motorcycle"}]
    assert choose_option(years, "3")["value"] == "Y3"
    assert choose_option(cls, "MCWG")["value"] == "C02"
    assert choose_option(cls, "HMV") is None


def el(idx, kind, label="", text="", options=None):
    return {"idx": idx, "tag": "x", "kind": kind, "type": "", "id": f"i{idx}", "name": "", "label": label,
            "text": text, "options": options or [], "error": ""}


def test_heuristic_maps_messy_labels():
    els = [el(0, "fill", "Name of Institute / University"), el(1, "fill", "Applicant's Name (as per records)"),
           el(2, "fill", "Gross Annual Household Income (in Rs.)"), el(3, "click", text="Save & Continue")]
    p = planner.heuristic_plan({"elements": els}, ["full_name", "college", "family_income"])
    assert dict(p["fills"]) == {"college": 0, "full_name": 1, "family_income": 2} and p["click"] == 3


def test_planner_never_picks_final_submit():
    els = [el(0, "click", text="Final Submit"), el(1, "click", text="Edit Details")]
    assert planner.plan({"elements": els, "title": "", "text": ""}, [], {})["state"] == "review"
    assert planner.heuristic_plan({"elements": [el(0, "click", text="Submit application")]}, [])["click"] is None


def llm_snapshot():
    return {"title": "t", "text": "x", "elements": [el(0, "fill", "Email"), el(1, "click", text="Save & Continue")]}


def test_llm_plan_accepted(monkeypatch):
    monkeypatch.setattr("config.llm_available", lambda: True)
    monkeypatch.setattr(extractor, "_call_llm",
                        lambda *a, **k: '{"state":"form","fills":[{"field":"email","element":0}],"click":1}')
    p = planner.plan(llm_snapshot(), ["email"], {"email": "Email"})
    assert p["mode"] == "llm" and p["fills"] == [("email", 0)] and p["click"] == 1


@pytest.mark.parametrize("reply", ["not json", '{"fills":[{"field":"cgpa","element":0}]}',
                                   '{"fills":[{"field":"email","element":99}]}', '{"fills":[],"click":null}'])
def test_bad_llm_plan_falls_back_to_rules(monkeypatch, reply):
    monkeypatch.setattr("config.llm_available", lambda: True)
    monkeypatch.setattr(extractor, "_call_llm", lambda *a, **k: reply)
    p = planner.plan(llm_snapshot(), ["email"], {"email": "Email"})
    assert p["mode"] == "rules" and p["fills"] == [("email", 0)]


@pytest.mark.parametrize("click", [2, 3])
def test_llm_cannot_click_final_or_blocked(monkeypatch, click):
    snap = {"title": "t", "text": "x", "elements": [el(0, "fill", "Email"), el(1, "click", text="Save & Continue"),
                                                    el(2, "click", text="Final Submit"), el(3, "click", text="Back")]}
    monkeypatch.setattr(extractor, "_call_llm", lambda *a, **k: f'{{"fills":[],"click":{click}}}')
    with pytest.raises(ValueError):
        planner.llm_plan(snap, ["email"], {"email": "Email"})
