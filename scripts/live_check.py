"""Live API-key check: proves every LLM-powered path works with YOUR key.

Usage:  python3 scripts/live_check.py
Setup:  put your key in .env (see .env.example) or export the env vars, e.g.
          export LLM_PROVIDER=anthropic
          export ANTHROPIC_API_KEY=sk-ant-...
        (or GEMINI_API_KEY=... / OPENAI_API_KEY=... with OPENAI_BASE_URL if needed)

Runs six checks against the configured provider and prints a PASS/FAIL table.
No check ever prints the key. All data used here is fictional demo data.
"""
import os
import socket
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

if os.getenv("DEMO_MODE", "").lower() == "true":
    print("note: DEMO_MODE=true found in environment; overriding to false for this live check.\n")
os.environ["DEMO_MODE"] = "false"
os.environ.setdefault("CIVICPILOT_DB", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "live_check.db"))

import logging
logging.getLogger("civicpilot").setLevel(logging.ERROR)

from core import automation, documents, extractor, planner, schema  # noqa: E402
from core.controller import Controller  # noqa: E402
from portal import server  # noqa: E402

DEMO_TEXT = ("Namaste, mera naam Aarav Sharma hai. Main Riverdale Institute of Technology mein "
             "second year B.Sc Physics padhta hoon. Meri family income 3.5 lakh hai aur CGPA 8.4 hai. "
             "Email aarav.sharma@example.edu hai.")
DEMO_PROFILE = {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
                "college": "Riverdale Institute of Technology", "course": "B.Sc Physics",
                "academic_year": "2", "family_income": "350000", "cgpa": "8.4"}

HINTS = ((401, "The API key was rejected (401). Check the key value and that it is active."),
         (403, "Access denied (403). The key may lack permission for this model."),
         (404, "Model not found (404). Set LLM_MODEL (and LLM_AGENT_MODEL) to a valid model id."),
         (429, "Rate limit or quota hit (429). Wait or check billing/quota."),
         (529, "Provider temporarily overloaded (529). Retry in a minute."))


def hint(e: Exception) -> str:
    s = str(e)
    for code, msg in HINTS:
        if str(code) in s:
            return msg
    if "timeout" in s.lower() or "connection" in s.lower():
        return "Network problem reaching the provider. Check connectivity or proxy."
    return ""


def banner():
    p = config.llm_provider()
    if not p:
        print("NO KEY FOUND.\nSet one of ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY"
              " (plus LLM_PROVIDER if ambiguous). See .env.example.\n")
        return None
    keys = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "openai_compat": "OPENAI_API_KEY"}
    k = os.getenv(keys[p], "")
    print("=" * 72)
    print(f"CivicPilot live check   provider={p}   key={keys[p]} set ({len(k)} chars, not shown)")
    print(f"  extract model : {config.llm_model('extract')}")
    print(f"  agent model   : {config.llm_model('agent')}")
    print("=" * 72)
    return p


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_controller(base):
    auto = SimpleNamespace(
        fill_form=lambda sid, v, k: automation.fill_form(sid, v, k, base),
        submit_application=lambda sid, v, k: automation.submit_application(sid, v, k, base),
        portal_status=lambda k: automation.portal_status(k, base),
        track_application=lambda ref: automation.track_application(ref, base),
        read_eligibility=lambda sid: automation.read_eligibility(sid, base),
        complete_otp=lambda sid, code, k: automation.complete_otp(sid, code, k, base))
    return Controller(automation=auto)


def marksheet_png() -> bytes:
    from playwright.sync_api import sync_playwright
    html = ("<html><body style='font-family:monospace;font-size:20px;padding:30px'>"
            "<h2>RIOT College &mdash; Marksheet (Fictional)</h2>"
            "<p>Name: Aarav Sharma<br>Course: B.Sc Physics<br>Year: Second Year<br>"
            "CGPA: 8.4<br>Family Income: Rs. 3,50,000<br>Email: aarav.sharma@example.edu</p></body></html>")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 420})
        pg.set_content(html)
        png = pg.screenshot()
        b.close()
    return png


def check_ping():
    reply = extractor._call_llm("Reply with exactly one word: PONG",
                                "You are a connectivity test. Reply with one word only.",
                                role="extract", max_tokens=16)
    assert "PONG" in reply.upper(), f"unexpected reply: {reply[:80]!r}"
    return "model answered a raw call"


def check_extraction():
    fields, mode, warn = extractor.extract(DEMO_TEXT, "scholarship")
    assert mode == "llm", f"extractor fell back to rules ({mode or 'demo'}) {warn}".strip()
    assert fields, "LLM returned no fields"
    got = ", ".join(f"{k}={v}" for k, v in sorted(fields.items()))
    assert fields.get("cgpa") == "8.4", f"CGPA not read correctly: got {sorted(fields)}"
    return f"extracted {len(fields)} fields -> {got}"


def check_routing():
    sid1 = extractor.classify_service("Mujhe apna driving licence renew karwana hai")
    sid2 = extractor.classify_service("I want money support for my college studies")
    assert sid1 == "licence", f"licence request routed to {sid1}"
    assert sid2 in (None, "scholarship"), f"scholarship request routed to {sid2}"
    return f"'licence renew' -> {sid1}, 'college money' -> {sid2 or 'asked user'}"


def check_planning():
    port = free_port()
    srv = server.start_in_thread(port)
    base = f"http://127.0.0.1:{port}/"
    try:
        with automation._browser(base) as (page, _viol):
            page.goto(f"{base}svc/scholarship/step/1?key=live-check-plan")
            snap = automation.snapshot(page)
        plan = planner.plan(snap, ["full_name", "email"], schema.get("scholarship").labels)
        assert plan["mode"] == "llm", "planner fell back to rules"
        assert {f for f, _ in plan["fills"]} <= {"full_name", "email"} and len(plan["fills"]) == 2
        return f"LLM mapped both fields to page elements (idx {[i for _, i in plan['fills']]})"
    finally:
        srv.shutdown()


def check_vision():
    png = marksheet_png()
    doc = documents.ingest("marksheet.png", png)
    assert doc["mode"] == "vision", f"expected vision mode, got {doc['mode']}"
    assert doc["fields"], "vision model returned no fields"
    return f"read {len(doc['fields'])} values from image: {', '.join(sorted(doc['fields']))}"


def check_end_to_end():
    port = free_port()
    srv = server.start_in_thread(port)
    base = f"http://127.0.0.1:{port}/"
    try:
        c = make_controller(base)
        c.analyze("Help me apply for the merit scholarship.", dict(DEMO_PROFILE), "scholarship")
        assert c.stage == 2, f"analyze failed: {c.message}"
        c.prepare()
        assert c.stage == 3 and c.auto and c.auto["ok"], f"prepare failed: {c.auto and c.auto['errors']}"
        c.proceed_to_approval()
        c.submit(confirmed=True)
        assert c.outcome == "accepted", f"submit outcome: {c.outcome} ({c.message})"
        app_id = c.receipt["application_id"]
        c.check_status()
        llm_steps = sum(1 for r in (c.auto.get("trace") or []) if r.get("planner") == "llm")
        return (f"full journey accepted: {app_id}, status now {c.message!r}; "
                f"{len(c.auto.get('trace') or [])} browser steps, {llm_steps} planned by LLM")
    finally:
        srv.shutdown()


CHECKS = [("1. raw API ping", check_ping),
          ("2. Hinglish extraction", check_extraction),
          ("3. service routing", check_routing),
          ("4. agent planning on live page", check_planning),
          ("5. vision document read", check_vision),
          ("6. FULL autonomous journey", check_end_to_end)]


def main():
    if banner() is None:
        return 1
    results, fail = [], 0
    for name, fn in CHECKS:
        t0 = time.time()
        try:
            detail = fn()
            results.append((name, True, f"{detail}   [{time.time() - t0:.1f}s]", ""))
        except Exception as e:
            fail += 1
            results.append((name, False, f"FAILED after {time.time() - t0:.1f}s: {type(e).__name__}: {e}", hint(e)))
    print()
    for name, ok, detail, h in results:
        print(("PASS  " if ok else "FAIL  ") + name)
        print(f"      {detail}")
        if h:
            print(f"      hint: {h}")
    print("-" * 72)
    print("ALL CHECKS PASSED - your key drives the whole pipeline." if not fail
          else f"{fail} of {len(results)} checks failed - see hints above.")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
