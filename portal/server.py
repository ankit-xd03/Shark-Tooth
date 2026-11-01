"""Local MOCK legacy-style government portal: server-rendered multi-page wizard plus a JSON status API.

Deliberately awkward, like real portals: a blocking cookie notice, a session-timeout page,
auto-generated element ids, labels that differ from the assistant's field names, coded dropdowns,
and no test hooks. Eligibility is decided on the server, independent of the assistant.

A seeded layout randomizer (P1-C) reshuffles labels, field order, ids, button text, dropdown wording
and adds decoy controls for keys like "bench-<seed>-...". It also powers a DD-MM-YYYY date variant
(P2-F). Tracking (P1-D), eligibility pages (P2-G) and an optional OTP challenge (P2-H) complete the
"legacy portal" experience. Everything is fictional.
"""
import html
import json
import os
import random
import re
import sys
import threading
import urllib.request
import uuid
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
from core import schema  # noqa: E402

MAX_INCOME = 800_000
MIN_CGPA = 6.0
GRACE_DAYS = 365
SUBSIDY_MAX_INCOME = 250_000

YEARS = [("", "-- Select --", ""), ("Y1", "1st Year", "1"), ("Y2", "2nd Year", "2"), ("Y3", "3rd Year", "3"),
         ("Y4", "4th Year", "4"), ("Y5", "5th Year", "5"), ("Y6", "6th Year", "6")]
YEARS_ALT = [("", "-- Choose year --", "")] + [(f"Y{i}", f"Year {i}", str(i)) for i in range(1, 7)]
CLASSES = [("", "-- Select --", ""), ("C01", "LMV - Light Motor Vehicle (Car)", "LMV"),
           ("C02", "MCWG - Motorcycle With Gear", "MCWG"), ("C03", "HMV - Heavy Motor Vehicle", "HMV")]
CLASSES_ALT = [("", "-- Choose class --", ""), ("C01", "Light Motor Vehicle (Car) - LMV", "LMV"),
               ("C02", "Motorcycle With Gear - MCWG", "MCWG"), ("C03", "Heavy Motor Vehicle - HMV", "HMV")]
CONN = [("", "-- Select --", ""), ("P1", "PM Ujjwala (PMUY)", "PMUY"), ("G1", "General / Non-Ujjwala", "GENERAL")]
CONN_ALT = [("", "-- Choose one --", ""), ("P1", "Ujjwala Scheme Connection (PMUY)", "PMUY"),
            ("G1", "Regular Connection (Non-PMUY)", "GENERAL")]

PORTALS = {
    "scholarship": {
        "title": "State Merit Scholarship Portal", "prefix": "SCH",
        "intro": "Apply online for the State Merit Scholarship. Keep your academic records ready.",
        "steps": [
            ("Personal Details", "Save & Continue",
             [("full_name", "Applicant's Name (as per records)", None), ("email", "E-mail ID", None)]),
            ("Institution Details", "Proceed",
             [("college", "Name of Institute / University", None), ("course", "Programme of Study", None),
              ("academic_year", "Current Year of Study", YEARS)]),
            ("Income and Academic Record", "Save and Review",
             [("family_income", "Gross Annual Household Income (in Rs.)", None),
              ("cgpa", "Aggregate CGPA (out of 10)", None)]),
        ],
    },
    "licence": {
        "title": "Regional Transport Office - Licence Renewal", "prefix": "DLR",
        "intro": "Renew your driving licence online. Licences can be renewed up to one year after expiry.",
        "steps": [
            ("Applicant Details", "Save & Continue",
             [("full_name", "Name of Licence Holder", None), ("email", "Email Address", None),
              ("date_of_birth", "Date of Birth (DD/MM/YYYY)", None)]),
            ("Licence Details", "Proceed",
             [("license_number", "Driving Licence Number", None),
              ("expiry_date", "Date of Expiry (DD/MM/YYYY)", None), ("vehicle_class", "Class of Vehicle", CLASSES)]),
            ("Address", "Save and Review", [("pincode", "PIN Code of Residence", None)]),
        ],
    },
    "subsidy": {
        "title": "LPG Connection Subsidy Claim Portal", "prefix": "LPG",
        "intro": "Claim the one-time LPG connection subsidy. Only PMUY (Ujjwala) connections are eligible.",
        "steps": [
            ("Applicant Details", "Save & Continue",
             [("full_name", "Applicant's Name", None), ("email", "Email Address", None)]),
            ("Connection Details", "Proceed",
             [("consumer_no", "LPG Consumer ID", None), ("connection_type", "Type of Connection", CONN)]),
            ("Bank and Income Details", "Save and Review",
             [("bank_ifsc", "IFSC Code", None), ("account_last4", "Last 4 Digits of Bank Account", None),
              ("annual_income", "Annual Household Income (in Rs.)", None)]),
        ],
    },
}

LABEL_VARIANTS = {
    "full_name": ["Applicant's Name (as per records)", "Name of Applicant", "Applicant Full Name",
                  "Candidate Name", "Name (as per records)"],
    "email": ["E-mail ID", "Email Address", "Contact Email", "Electronic Mail"],
    "college": ["Name of Institute / University", "College / Institution Name", "Educational Institution",
                "University / College"],
    "course": ["Programme of Study", "Course / Degree", "Degree Programme", "Stream / Branch"],
    "academic_year": ["Current Year of Study", "Year of Study", "Academic Year", "Study Year"],
    "family_income": ["Gross Annual Household Income (in Rs.)", "Annual Family Income",
                      "Total Annual Income (INR)", "Yearly Income"],
    "annual_income": ["Annual Household Income (in Rs.)", "Yearly Family Income", "Total Annual Income"],
    "cgpa": ["Aggregate CGPA (out of 10)", "Cumulative GPA", "Grade Point Average", "CGPA"],
    "date_of_birth": ["Date of Birth (DD/MM/YYYY)", "DOB (DD/MM/YYYY)", "Birth Date (DD/MM/YYYY)"],
    "license_number": ["Driving Licence Number", "DL Number", "Licence No.", "Driving Licence No."],
    "expiry_date": ["Date of Expiry (DD/MM/YYYY)", "Licence Expiry Date (DD/MM/YYYY)",
                    "Valid Upto (DD/MM/YYYY)"],
    "vehicle_class": ["Class of Vehicle", "Vehicle Category", "Class of Licence"],
    "pincode": ["PIN Code of Residence", "Postal PIN Code", "Area PIN Code", "Residence PIN"],
    "consumer_no": ["LPG Consumer ID", "Consumer Number", "LPG Connection Number"],
    "connection_type": ["Type of Connection", "Connection Category", "Scheme Type"],
    "bank_ifsc": ["IFSC Code", "Bank IFSC", "Branch IFSC Code"],
    "account_last4": ["Last 4 Digits of Bank Account", "Bank A/c (Last 4 Digits)", "Account Last Four Digits"],
}
DECOY_FIELDS = ["Father's / Husband's Name", "Mobile Number", "Aadhaar Enrolment Number", "Blood Group",
                "Religion", "Ward Number", "Emergency Contact Number", "Medium of Instruction"]
DECOY_BUTTONS = ["Print Form", "Help", "Feedback", "Download Guidelines"]
BUTTON_VARIANTS = [["Save & Continue", "Save and Proceed", "Continue"],
                   ["Proceed", "Next Step", "Save & Next"],
                   ["Save and Review", "Review Application", "Proceed to Review"]]
OPTION_VARIANTS = {"academic_year": [YEARS, YEARS_ALT], "vehicle_class": [CLASSES, CLASSES_ALT],
                   "connection_type": [CONN, CONN_ALT]}

_layouts: dict = {}


def _canonical_layout(sid):
    cached = _layouts.get(("canonical", sid))
    if cached:
        return cached
    labels, rows, buttons = {}, {}, {}
    for n, (_, button, fields) in enumerate(PORTALS[sid]["steps"]):
        rows[n] = [("field", name) for name, _, _ in fields]
        buttons[n] = button
        for name, label, _opts in fields:
            labels[name] = label
    layout = {"labels": labels, "rows": rows, "buttons": buttons, "decoy_buttons": {n: [] for n in rows},
              "options": {}, "date_hyphen": False, "interstitial": False, "id_sfx": ""}
    _layouts[("canonical", sid)] = layout
    return layout


def _build_ids():
    ids = {}
    for sid, p in PORTALS.items():
        n = 0
        for _, _, fields in p["steps"]:
            for name, _, opts in fields:
                n += 1
                ids[(sid, name)] = f"ctl00_ContentPlaceHolder1_{'ddl' if opts else 'txt'}{n:02d}"
    return ids


IDS = _build_ids()
_lock = threading.Lock()
_records: dict = {}
_sessions: dict = {}


def _seed_of(key: str):
    if key.startswith("bench-"):
        tail = key.split("-")[1]
        if tail.isdigit():
            return int(tail)
    env = os.getenv("PORTAL_SEED", "").strip()
    return int(env) if env.isdigit() else None


def layout_for(sid: str, key: str) -> dict:
    """Deterministic page layout for a (service, seed) pair; canonical layout when unseeded."""
    seed = _seed_of(key)
    hyphen_env = os.getenv("PORTAL_DATE_HYPHENS", "").lower() == "true"
    seed_env = os.getenv("PORTAL_SEED", "").strip()
    if seed is None and not seed_env.isdigit() and not hyphen_env:
        return _canonical_layout(sid)
    cache_key = (sid, seed, seed_env, hyphen_env)
    if cache_key in _layouts:
        return _layouts[cache_key]
    rng = random.Random(f"{sid}:{seed if seed is not None else (int(seed_env) if seed_env.isdigit() else 0)}")
    layout = {"labels": {}, "rows": {}, "buttons": {}, "decoy_buttons": {}, "options": {},
              "date_hyphen": hyphen_env or rng.random() < 0.4,
              "interstitial": rng.random() < 0.35,
              "id_sfx": f"_x{uuid.UUID(int=rng.getrandbits(32), version=4).hex[:6]}"}
    if not any(schema.get_field_kind(f) == "date" for _, _, fields in PORTALS[sid]["steps"]
               for f, _, _ in fields):
        layout["date_hyphen"] = False
    for n, (_, _, fields) in enumerate(PORTALS[sid]["steps"]):
        rows, decoys = [], rng.sample(DECOY_FIELDS, k=rng.randint(0, 2)) if rng.random() < 0.7 else []
        for name, label, _opts in fields:
            layout["labels"][name] = rng.choice(LABEL_VARIANTS.get(name, [label]))
            if name in OPTION_VARIANTS:
                layout["options"][name] = rng.choice(OPTION_VARIANTS[name])
            rows.append(("field", name))
        for d in decoys:
            rows.insert(rng.randint(0, len(rows)), ("decoy", d))
        layout["rows"][n] = rows
        layout["buttons"][n] = rng.choice(BUTTON_VARIANTS[n])
        layout["decoy_buttons"][n] = rng.sample(DECOY_BUTTONS, k=rng.randint(0, 2))
    _layouts[cache_key] = layout
    return layout


def _chaos() -> bool:
    return os.getenv("PORTAL_CHAOS", "true").lower() != "false"


def _otp_enabled() -> bool:
    return os.getenv("PORTAL_OTP", "false").lower() == "true"


def _track_delay() -> int:
    try:
        return int(os.getenv("PORTAL_TRACK_DELAY_SECONDS", "90"))
    except ValueError:
        return 90


def _session(key):
    return _sessions.setdefault(key, {"data": {}, "expired": False})


def _esc(s):
    return html.escape(str(s), quote=True)


CSS = """body{font-family:Verdana,sans-serif;margin:0;background:#eef1f6;color:#222}
header{background:#1d3f72;color:#fff;padding:12px 22px;display:flex;justify-content:space-between;align-items:center}
.mock{background:#ffcf33;color:#3a2c00;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700}
main{max-width:680px;margin:22px auto;padding:0 14px}
section{background:#fff;border:1px solid #c9d2e0;padding:18px 24px;margin-bottom:14px}
label{display:block;margin:12px 0 4px;font-weight:bold;font-size:13px}
input[type=text],select{width:100%;padding:8px;border:1px solid #9aa7bd;font-size:14px;box-sizing:border-box}
.btn,input[type=submit],input[type=reset],button{margin:16px 8px 0 0;padding:9px 18px;border:0;background:#1d3f72;
color:#fff;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}
input[type=reset],.btn.alt{background:#7a8599}.err{color:#b00020;font-size:12px;display:block;margin-top:3px}
table{width:100%;border-collapse:collapse}td{padding:6px;border-bottom:1px solid #dde3ee;font-size:14px}
td:first-child{font-weight:bold;width:45%}
#cookie{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:99}
#cookie .dlg{background:#fff;padding:22px 28px;max-width:420px}.ok{border-left:6px solid #1c7c3b}.bad{border-left:6px solid #b00020}
.note{background:#f4f6fb;border:1px dashed #9aa7bd;padding:10px 14px;font-size:13px}"""


def _page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{_esc(title)}</title>'
            f'<style>{CSS}</style></head><body><header><b>{_esc(title)}</b>'
            f'<span class="mock">MOCK PORTAL - FICTIONAL DATA ONLY</span></header><main>{body}</main></body></html>')


def _home():
    links = "".join(f'<li><a href="/svc/{sid}/?key=manual-{uuid.uuid4().hex[:6]}">{_esc(p["title"])}</a></li>'
                    for sid, p in PORTALS.items())
    return _page("Mock Government Services",
                 f"<section><h2>Services</h2><ul>{links}</ul>"
                 f'<p><a href="/track">Track an application</a></p></section>')


def _landing(sid, key):
    p = PORTALS[sid]
    notice = ('<div id="cookie"><div class="dlg"><h3>Notice</h3><p>This website uses cookies and records your '
              'session. By continuing you accept the terms of use.</p>'
              '<button type="button" onclick="document.getElementById(\'cookie\').style.display=\'none\'">'
              'Accept and continue</button></div></div>')
    body = (f'{notice}<section><h2>{_esc(p["title"])}</h2><p>{_esc(p["intro"])}</p>'
            f'<a class="btn" href="/svc/{sid}/eligibility?key={quote(key)}">Check Eligibility</a> '
            f'<a class="btn" href="/svc/{sid}/step/1?key={quote(key)}">Start New Application</a></section>')
    return _page(p["title"], body)


def _expired(sid, key):
    body = (f'<section class="bad"><h2>Session Timeout</h2><p>Your session has expired due to inactivity.</p>'
            f'<a class="btn" href="/svc/{sid}/step/2?key={quote(key)}&amp;resume=1">Click here to log in again</a></section>')
    return _page(PORTALS[sid]["title"], body)


def _instructions(sid, key):
    body = (f'<section><h2>Important Instructions</h2>'
            f'<p class="note">Before you begin: keep scanned documents ready, use the exact spelling from your '
            f'records, and do not press the browser back button. Applications with mismatched details are rejected.</p>'
            f'<a class="btn" href="/svc/{sid}/step/1?key={quote(key)}&amp;ack=1">I Acknowledge and Continue</a></section>')
    return _page(PORTALS[sid]["title"], body)


def _eligibility_page(sid):
    p = PORTALS[sid]
    if sid == "scholarship":
        rules = (f"<li>Annual family income must not exceed INR {MAX_INCOME:,}.</li>"
                 f"<li>Minimum aggregate CGPA of {MIN_CGPA} out of 10.</li>")
    elif sid == "licence":
        rules = (f"<li>The licence must have expired no more than {GRACE_DAYS} days ago.</li>"
                 "<li>The applicant must be at least 18 years old.</li>")
    else:
        rules = (f"<li>Annual household income must not exceed INR {SUBSIDY_MAX_INCOME:,}.</li>"
                 "<li>The connection must be under the PMUY (Ujjwala) scheme.</li>")
    body = (f'<section><h2>Eligibility - {_esc(p["title"])}</h2><p>To qualify for this service you must meet '
            f'every rule below. Applications are checked again on the server before acceptance.</p>'
            f'<ul>{rules}</ul></section>')
    return _page(p["title"], body)


ELIGIBILITY_RULES = {
    "scholarship": {"income_max": MAX_INCOME, "min_cgpa": MIN_CGPA},
    "licence": {"grace_days": GRACE_DAYS},
    "subsidy": {"income_max": SUBSIDY_MAX_INCOME, "connection": "PMUY"},
}


def _display_value(opts, canonical):
    for pv, _, canon in opts or []:
        if canon == canonical:
            return pv
    return canonical


def _fid(sid, name, key):
    layout = layout_for(sid, key)
    return f"{IDS[(sid, name)]}{layout['id_sfx']}"


def _render_step(sid, n, key, values, errors):
    p = PORTALS[sid]
    layout = layout_for(sid, key)
    title = p["steps"][n - 1][0]
    rows = []
    for i, (kind, item) in enumerate(layout["rows"][n - 1]):
        if kind == "decoy":
            did = f"decoy{i:02d}{layout['id_sfx']}"
            rows.append(f'<label for="{did}">{_esc(item)}</label>'
                        f'<input type="text" id="{did}" name="{did}" value="">')
            continue
        name = item
        label = layout["labels"].get(name) or dict((fn, lb) for fn, lb, _ in p["steps"][n - 1][2])[name]
        opts = layout["options"].get(name)
        if opts is None:
            opts = next((o for fn, _, o in p["steps"][n - 1][2] if fn == name and o), None)
        fid = _fid(sid, name, key)
        val = values.get(name, "")
        if opts:
            options = "".join(f'<option value="{_esc(pv)}"{" selected" if pv == val else ""}>{_esc(text)}</option>'
                              for pv, text, _ in opts)
            control = f'<select id="{fid}" name="{fid}">{options}</select>'
        else:
            control = f'<input type="text" id="{fid}" name="{fid}" value="{_esc(val)}">'
        err = f'<span class="err">{_esc(errors[name])}</span>' if name in errors else ""
        rows.append(f'<label for="{fid}">{_esc(label)}</label>{control}{err}')
    button = layout["buttons"].get(n - 1) or p["steps"][n - 1][1]
    decoys = "".join(f'<input type="button" value="{_esc(b)}">' for b in layout["decoy_buttons"].get(n - 1, []))
    back = (f'<a class="btn alt" href="/svc/{sid}/step/{n - 1}?key={quote(key)}&amp;resume=1">Back</a>'
            if n > 1 else "")
    body = (f'<section><h2>Step {n} of {len(p["steps"])} - {_esc(title)}</h2>'
            f'<form method="post" action="/svc/{sid}/step/{n}?key={quote(key)}">{"".join(rows)}'
            f'{decoys}<input type="submit" value="{_esc(button)}"><input type="reset" value="Clear">{back}</form></section>')
    return _page(p["title"], body)


def _review_value(sid, name, canonical, key):
    layout = layout_for(sid, key)
    opts = layout["options"].get(name)
    if opts is None:
        for _, _, fields in PORTALS[sid]["steps"]:
            for fname, _, o in fields:
                if fname == name and o:
                    opts = o
    for _, text, canon in opts or []:
        if canon == canonical:
            return text
    return canonical


def _render_review(sid, key, data):
    p = PORTALS[sid]
    layout = layout_for(sid, key)
    rows = "".join(f"<tr><td>{_esc(layout['labels'].get(name, label))}</td>"
                   f"<td>{_esc(_review_value(sid, name, data[name], key))}</td></tr>"
                   for _, _, fields in p["steps"] for name, label, _ in fields)
    body = (f'<section><h2>Review Application</h2><table>{rows}</table>'
            f'<form method="post" action="/svc/{sid}/submit?key={quote(key)}">'
            f'<input type="submit" value="Final Submit"></form>'
            f'<a class="btn alt" href="/svc/{sid}/step/1?key={quote(key)}&amp;resume=1">Edit Details</a></section>')
    return _page(p["title"], body)


def _render_result(sid, rec):
    if rec["status"] == "ACCEPTED":
        body = (f'<section class="ok"><h2>Application Submitted Successfully</h2>'
                f'<p>Application Reference No: <b>{_esc(rec["application_id"])}</b></p>'
                f'<p>Status: <b>{_esc(rec["status"])}</b></p>'
                f'<p>Submitted on (UTC): <b>{_esc(rec["submitted_at"])}</b></p></section>')
    else:
        body = (f'<section class="bad"><h2>Application Rejected</h2>'
                f'<p>Reason: {_esc(rec["reason"])}</p></section>')
    return _page(PORTALS[sid]["title"], body)


def _otp_page(sid, key, error=""):
    err = f'<span class="err">{_esc(error)}</span>' if error else ""
    body = (f'<section><h2>Verify OTP</h2>'
            f'<p>An OTP has been sent to your registered mobile number. Enter the 6-digit code to continue.</p>'
            f'<form method="post" action="/svc/{sid}/otp?key={quote(key)}">'
            f'<label for="otp_input">Enter 6-digit OTP</label>'
            f'<input type="text" id="otp_input" name="otp" value="">{err}'
            f'<input type="submit" value="Verify OTP"></form></section>')
    return _page(PORTALS[sid]["title"], body)


def _sms_page(key):
    sess = _session(key)
    code = sess.get("otp")
    msg = (f"Your CivicPortal OTP is {code}. It expires in 10 minutes. "
           "Never share your OTP with anyone, even if the caller claims to be from the government.") if code \
        else "No OTP messages right now."
    body = (f'<section><h2>Simulated SMS Inbox</h2>'
            f'<p class="note"><b>From:</b> VM-CIVICPORTAL<br><b>Message:</b> {_esc(msg)}</p></section>')
    return _page("Simulated SMS Inbox", body)


def _step_errors(sid, n, posted, key):
    svc = schema.get(sid)
    layout = layout_for(sid, key)
    values, errors, canon = {}, {}, {}
    for name, _, opts in PORTALS[sid]["steps"][n - 1][2]:
        raw = (posted.get(_fid(sid, name, key)) or "").strip()
        values[name] = raw
        if opts:
            match = next((c for pv, _, c in opts if pv == raw and pv), "")
            raw_canon = match
        else:
            raw_canon = raw
        if layout["date_hyphen"] and schema.get_field_kind(name) == "date":
            if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", raw):
                errors[name] = "Use the DD-MM-YYYY format with hyphens (e.g. 15-12-2026)."
                continue
        if not raw_canon:
            errors[name] = "This field is required."
            continue
        try:
            svc.validators[name](raw_canon)
            canon[name] = raw_canon
        except ValueError as e:
            errors[name] = str(e)
    return values, errors, canon


def _decide(sid, clean):
    if sid == "scholarship":
        if clean["family_income"] > MAX_INCOME:
            return f"Family income exceeds the eligibility limit of INR {MAX_INCOME:,}."
        if clean["cgpa"] < MIN_CGPA:
            return f"CGPA is below the minimum of {MIN_CGPA}."
    if sid == "licence" and (date.today() - clean["expiry_date"]).days > GRACE_DAYS:
        return "Licence expired more than one year ago. Renewal is not permitted; a fresh licence test is required."
    if sid == "subsidy":
        if clean["annual_income"] > SUBSIDY_MAX_INCOME:
            return f"Annual income exceeds the PMUY subsidy limit of INR {SUBSIDY_MAX_INCOME:,}."
        if clean["connection_type"] != "PMUY":
            return "This subsidy is available only for PMUY (Ujjwala) scheme connections."
    return None


def tracked_status(rec):
    """Official status shown on the tracking page; progresses with time (configurable delay)."""
    if rec["status"] != "ACCEPTED":
        return rec["status"]
    try:
        then = datetime.fromisoformat(rec["submitted_at"])
    except (ValueError, TypeError):
        return "UNDER REVIEW"
    elapsed = (datetime.now(timezone.utc) - then).total_seconds()
    delay = max(_track_delay(), 0)
    if elapsed < delay / 3:
        return "SUBMITTED"
    if elapsed < delay:
        return "UNDER REVIEW"
    return "APPROVED"


def _record_by_ref(ref):
    for rec in _records.values():
        if rec.get("application_id") == ref:
            return rec
    return None


def _create_record(sid, key):
    data = dict(_session(key)["data"])
    clean, errors, missing = schema.get(sid).validate(data)
    if errors or missing:
        return ("incomplete", None)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    reason = _decide(sid, clean)
    if reason:
        rec = {"status": "REJECTED", "submitted_at": now, "reason": reason, "service": sid}
    else:
        rec = {"status": "ACCEPTED", "submitted_at": now, "service": sid,
               "application_id": f"{PORTALS[sid]['prefix']}-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}",
               "applicant": clean["full_name"]}
    _records[key] = rec
    return ("ok", rec)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", headers=None):
        if isinstance(body, str):
            raw, ctype = body.encode(), "text/html; charset=utf-8"
        elif isinstance(body, bytes):
            raw = body
        else:
            raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, location):
        self._send(302, b"", "text/plain", {"Location": location})

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        key = q.get("key", [""])[0] or f"manual-{uuid.uuid4().hex[:8]}"
        parts = [p for p in u.path.split("/") if p]
        if not parts:
            return self._send(200, _home())
        if parts == ["api", "health"]:
            return self._send(200, {"ok": True, "service": "civicpilot-mock-portal"})
        if parts == ["api", "status"]:
            rec = _records.get(q.get("key", [""])[0])
            return self._send(200, {"found": rec is not None, "record": rec})
        if parts == ["api", "track"]:
            ref = q.get("ref", [""])[0]
            rec = _record_by_ref(ref)
            return self._send(200, {"found": rec is not None, "application_status":
                                    tracked_status(rec) if rec else None,
                                    "submitted_at": rec.get("submitted_at") if rec else None})
        if parts == ["api", "eligibility"]:
            sid = q.get("service", [""])[0]
            return self._send(200, ELIGIBILITY_RULES.get(sid, {"error": "unknown service"}))
        if parts == ["track"]:
            return self._send(200, _track_page(q.get("ref", [""])[0]))
        if parts == ["sms"]:
            return self._send(200, _sms_page(key))
        if len(parts) >= 2 and parts[0] == "svc" and parts[1] in PORTALS:
            sid = parts[1]
            if len(parts) == 2:
                return self._send(200, _landing(sid, key))
            if len(parts) == 3 and parts[2] == "eligibility":
                return self._send(200, _eligibility_page(sid))
            if len(parts) == 4 and parts[2] == "step" and parts[3].isdigit():
                return self._step_get(sid, int(parts[3]), key, q)
            if len(parts) == 3 and parts[2] == "review":
                return self._review_get(sid, key)
            if len(parts) == 3 and parts[2] == "otp":
                return self._send(200, _otp_page(sid, key))
        self._send(404, {"error": "not found"})

    def _step_get(self, sid, n, key, q):
        if not 1 <= n <= len(PORTALS[sid]["steps"]):
            return self._send(404, {"error": "not found"})
        layout = layout_for(sid, key)
        with _lock:
            sess = _session(key)
            if n == 1 and layout["interstitial"] and "ack" not in q:
                return self._send(200, _instructions(sid, key))
            if n == 2 and _chaos() and not sess["expired"] and "resume" not in q:
                sess["expired"] = True
                return self._send(200, _expired(sid, key))
            values = {name: _display_value(layout["options"].get(name) or opts, sess["data"].get(name, ""))
                      for name, _, opts in PORTALS[sid]["steps"][n - 1][2]}
        self._send(200, _render_step(sid, n, key, values, {}))

    def _review_get(self, sid, key):
        with _lock:
            data = dict(_session(key)["data"])
        for n, (_, _, fields) in enumerate(PORTALS[sid]["steps"], 1):
            if any(name not in data for name, _, _ in fields):
                return self._redirect(f"/svc/{sid}/step/{n}?key={quote(key)}&resume=1")
        self._send(200, _render_review(sid, key, data))

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 20_000:
                return self._send(413, {"error": "payload too large"})
            posted = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"error": "invalid body"})
        u = urlparse(self.path)
        key = parse_qs(u.query).get("key", [""])[0]
        parts = [p for p in u.path.split("/") if p]
        if not key or len(parts) < 3 or parts[0] != "svc" or parts[1] not in PORTALS:
            return self._send(404, {"error": "not found"})
        sid = parts[1]
        if parts[2] == "step" and len(parts) == 4 and parts[3].isdigit():
            return self._step_post(sid, int(parts[3]), key, posted)
        if parts[2] == "otp":
            return self._otp_post(sid, key, posted)
        if parts[2] == "submit":
            return self._submit(sid, key)
        self._send(404, {"error": "not found"})

    def _step_post(self, sid, n, key, posted):
        steps = PORTALS[sid]["steps"]
        if not 1 <= n <= len(steps):
            return self._send(404, {"error": "not found"})
        values, errors, canon = _step_errors(sid, n, posted, key)
        if errors:
            return self._send(200, _render_step(sid, n, key, values, errors))
        with _lock:
            _session(key)["data"].update(canon)
        nxt = f"/svc/{sid}/step/{n + 1}" if n < len(steps) else f"/svc/{sid}/review"
        self._redirect(f"{nxt}?key={quote(key)}")

    def _otp_post(self, sid, key, posted):
        with _lock:
            sess = _session(key)
            code = (posted.get("otp") or "").strip()
            if code and code == sess.get("otp"):
                sess["otp_ok"] = True
                status, rec = _create_record(sid, key)
                if status == "incomplete":
                    return self._send(422, _page("Incomplete application",
                                                 "<section class='bad'><h2>Application incomplete</h2></section>"))
                return self._send(200, _render_result(sid, rec))
            sess["otp_attempts"] = sess.get("otp_attempts", 0) + 1
        return self._send(200, _otp_page(sid, key, "Incorrect OTP. Check the SMS inbox and try again."))

    def _submit(self, sid, key):
        with _lock:
            if key in _records:
                return self._send(200, _render_result(sid, _records[key]))
            if _otp_enabled() and not _session(key).get("otp_ok"):
                sess = _session(key)
                if not sess.get("otp"):
                    sess["otp"] = f"{random.randint(100000, 999999)}"
                    sess["otp_attempts"] = 0
                return self._send(200, _otp_page(sid, key))
            status, rec = _create_record(sid, key)
            if status == "incomplete":
                return self._send(422, _page("Incomplete application",
                                             "<section class='bad'><h2>Application incomplete</h2></section>"))
        self._send(200, _render_result(sid, rec))


def _track_page(ref):
    rec = _record_by_ref(ref)
    if rec:
        rows = (f"<tr><td>Application Reference No</td><td>{_esc(rec['application_id'])}</td></tr>"
                f"<tr><td>Current Status</td><td><b>{_esc(tracked_status(rec))}</b></td></tr>"
                f"<tr><td>Submitted on (UTC)</td><td>{_esc(rec['submitted_at'])}</td></tr>")
        body = f'<section><h2>Track Application</h2><table>{rows}</table></section>'
    else:
        body = ('<section><h2>Track Application</h2>'
                '<p class="note">No application found for that reference.</p></section>')
    body += (f'<form method="get" action="/track"><label for="ref">Application Reference</label>'
             f'<input type="text" id="ref" name="ref" value="{_esc(ref)}">'
             f'<input type="submit" value="Track"></form>')
    return _page("Application Tracking", body)


def is_up(port=None) -> bool:
    """True only when the CivicPilot mock portal itself answers (not some other program on the port)."""
    try:
        url = f"http://{config.PORTAL_HOST}:{port or config.PORTAL_PORT}/api/health"
        with urllib.request.urlopen(url, timeout=1) as r:
            return r.status == 200 and json.loads(r.read() or b"{}").get("ok") is True
    except Exception:
        return False


def start_in_thread(port=None) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((config.PORTAL_HOST, port if port is not None else config.PORTAL_PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def ensure_running():
    """Start the portal unless it is already up. Raises OSError when another program owns the port."""
    return None if is_up() else start_in_thread()


if __name__ == "__main__":
    print(f"Mock portal on {config.PORTAL_URL}  (Ctrl+C to stop)")
    ThreadingHTTPServer((config.PORTAL_HOST, config.PORTAL_PORT), Handler).serve_forever()
