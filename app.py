"""CivicPilot AI - Streamlit UI. Run: streamlit run app.py"""
import json
import logging
from pathlib import Path

import streamlit as st

import config
from core import audit, preflight, schema, store
from core.controller import Controller
from core.i18n import LANGUAGES, stages
from core.i18n import t as _t
from portal import server as portal_server

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

st.set_page_config(page_title="CivicPilot AI", page_icon="🏛️", layout="wide")

st.session_state.setdefault("lang", "en")


def t(key: str, **fmt) -> str:
    """UI-string wrapper: resolves the key in the language chosen in the sidebar."""
    return _t(key, st.session_state.get("lang", "en"), **fmt)


DEMO_PROFILES = {
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
DEMO_REQUESTS = {
    "scholarship": "Hi, I'm a third-year student and I need help applying for the state merit scholarship.",
    "licence": "Hi, I need to renew my driving licence before it expires.",
    "subsidy": "Namaste, I have a PMUY Ujjwala LPG connection, consumer ID 5500012345, and I want to claim the subsidy.",
}


@st.cache_resource
def start_portal() -> str:
    """Start the mock portal once per server. Returns '' or a short error (e.g. port already in use)."""
    try:
        portal_server.ensure_running()
        return ""
    except OSError as e:
        return f"{type(e).__name__}: {e}"


@st.cache_resource(show_spinner=False)
def browser_checks() -> list:
    """Python + Playwright Chromium launch test, cached per server (cleared by 'Re-check setup')."""
    return preflight.run_all(include_portal=False)


portal_error = start_portal()

if "ctl" not in st.session_state:
    st.session_state.ctl = Controller()
ctl: Controller = st.session_state.ctl
st.session_state.setdefault("request_text", "")
st.session_state.setdefault("svc", "scholarship")
for n in schema.ALL_FIELD_NAMES:
    st.session_state.setdefault(f"in_{n}", "")
for k, v in (st.session_state.pop("_pending", None) or {}).items():
    st.session_state[k] = v

svc = schema.get(st.session_state["svc"])
if ctl.stage >= 1:
    svc = ctl.service


def profile_inputs() -> dict:
    return {n: st.session_state[f"in_{n}"] for n in schema.ALL_FIELD_NAMES}


def load_demo(sid: str, drop: str = ""):
    ctl.reset()
    st.session_state["chat"] = []
    for n in schema.ALL_FIELD_NAMES:
        st.session_state[f"in_{n}"] = DEMO_PROFILES[sid].get(n, "")
    if drop:
        st.session_state[f"in_{drop}"] = ""
    st.session_state["request_text"] = DEMO_REQUESTS[sid]
    st.session_state["svc"] = sid


def change_service():
    ctl.reset()


def start_over():
    ctl.reset()
    st.session_state["chat"] = []
    st.session_state["request_text"] = ""
    st.session_state["confirm"] = False
    for n in schema.ALL_FIELD_NAMES:
        st.session_state[f"in_{n}"] = ""


def push_fields_to_inputs():
    st.session_state["_pending"] = {"svc": ctl.service.id,
                                    **{f"in_{n}": ctl.fields[n] for n in ctl.service.names}}


def review_table():
    values = ctl.service.form_values(ctl.clean)
    st.table({ctl.service.labels[n]: [values.get(n, "-")] for n in ctl.service.names})


def trace_table(a):
    if a and a.get("trace"):
        labels = ctl.service.labels
        with st.expander(t("trace_title"), expanded=False):
            st.dataframe([{k: v for k, v in row.items() if k != "shot"} for row in a["trace"]],
                         hide_index=True, width="stretch")
            shots = a.get("shots") or []
            for i, row in enumerate(a["trace"]):
                filled = ", ".join(labels.get(f, f) for f in row["filled"].split(", ") if f and f != "-")
                head = t("trace_step", step=row["step"], page=row["page"], planner=row["planner"])
                if filled:
                    head += " · " + t("trace_filled", f=filled)
                if row["action"] != "-":
                    head += " · " + t("trace_action", a=row["action"])
                with st.expander(head, expanded=False):
                    if row.get("note"):
                        st.caption(t("trace_note", note=row["note"]))
                    if i < len(shots) and shots[i]:
                        st.image(shots[i], caption=t("shot_caption", step=row["step"]),
                                 width="stretch")
            st.caption(t("trace_caption"))


def chat_panel():
    if ctl.stage < 1 or ctl.stage >= 3 or not (ctl.missing or ctl.errors):
        return
    st.divider()
    st.subheader(t("chat"))
    st.caption(t("chat_caption"))
    for m in st.session_state.get("chat", []):
        with st.chat_message(m["role"]):
            st.write(m["text"])
    q = ctl.chat_question()
    if q:
        with st.chat_message("assistant"):
            err = t("chat_portal_err", err=q["error"]) if q["error"] else ""
            st.write(f"{q['question']}  _{q['example']}_".strip() + err)
    st.chat_input(t("chat_input"), key="chat_in", on_submit=on_chat_submit)


def on_chat_submit():
    """Runs before the next script run, so the profile boxes can be updated safely. Without this, a
    chat answer was invisible in the profile and a later "Save & re-validate" wiped it."""
    user = st.session_state.get("chat_in")
    if not user:
        return
    c: Controller = st.session_state.ctl
    st.session_state.setdefault("chat", []).append({"role": "user", "text": user})
    st.session_state["chat"].append({"role": "assistant", "text": c.chat_reply(user)})
    for n in c.service.names:
        st.session_state[f"in_{n}"] = c.fields[n]


def automation_status():
    a = ctl.auto
    if not a:
        return
    labels = ctl.service.labels
    st.subheader(t("auto_header"))
    c1, c2, c3 = st.columns(3)
    c1.metric(t("fields_completed"), f"{len(a['completed'])}/{len(ctl.service.names)}")
    c2.write(f"**{t('completed')}:** " + (", ".join(labels[f] for f in a["completed"]) or t("none")))
    c3.write(f"**{t('outstanding')}:** " + (", ".join(labels[f] for f in a["outstanding"]) or t("none")))
    for e in a["errors"]:
        st.error(e)
    for f, m in a["field_errors"].items():
        st.error(t("portal_says", field=labels.get(f, f), msg=m))
    trace_table(a)


def receipt_text(r):
    return "\n".join([t("receipt_title", title=ctl.service.title),
                      f"{t('app_id')}: {r['application_id']}",
                      f"{t('status_word')}: {r['status']}",
                      f"{t('submitted_at')}: {r['submitted_at']}",
                      t("receipt_note")])


with st.sidebar:
    st.selectbox(t("lang_picker"), list(LANGUAGES.keys()), key="lang",
                 format_func=lambda c: LANGUAGES[c])
    st.header(t("progress"))
    st.progress(min(ctl.stage / 5, 1.0), text=t("stage_progress", n=ctl.stage))
    for i, name in enumerate(stages(st.session_state["lang"])):
        st.write(("✅ " if ctl.stage > i else "⏳ " if ctl.stage == i else "▫️ ") + name)
    st.divider()
    llm_on = config.llm_available() and not (ctl.stage >= 1 and ctl.mode == "demo")
    st.write("**Mode:** " + (t("mode_llm") if llm_on else t("mode_demo")))
    st.caption(t("portal_caption", url=config.PORTAL_URL))
    with st.expander(t("activity_log")):
        st.code("\n".join(ctl.events) or t("no_activity"))
    with st.expander(t("past_apps")):
        hist = store.history()
        if hist:
            st.dataframe(hist, hide_index=True, width="stretch")
        else:
            st.caption(t("nothing_yet"))
    st.button(t("start_over"), on_click=start_over)

st.title(t("app_title"))
st.caption(t("app_caption"))
st.info(t("proto_banner"), icon="ℹ️")
if not config.llm_available():
    st.warning(t("demo_warning"), icon="🧪")
if ctl.warning:
    st.warning(ctl.warning)
with st.spinner(t("setup_spinner")):
    setup_problems = [c for c in browser_checks() + [preflight.check_portal(portal_error)] if not c["ok"]]
if setup_problems:
    for c in setup_problems:
        st.error(t("setup_problem", title=c["title"], detail=c["detail"], fix=c["fix"]), icon="🛠️")
    if st.button(t("setup_recheck")):
        browser_checks.clear()
        start_portal.clear()
        st.rerun()

if ctl.stage == 5 and ctl.receipt:
    st.success(t("submitted_ok"), icon="✅")
    r = ctl.receipt
    c1, c2, c3 = st.columns(3)
    c1.metric(t("app_id"), r["application_id"])
    c2.metric(t("status_at_submit"), r["status"])
    c3.metric(t("submitted_at"), r["submitted_at"])
    st.subheader(t("live_tracking"))
    if ctl.tracking:
        b1, b2 = st.columns([1, 3])
        b1.metric(t("portal_status_now"), ctl.tracking["status"])
        b2.caption(t("tracking_caption", ref=ctl.tracking["ref"]))
    elif ctl.message:
        st.warning(ctl.message)
    if st.button(t("refresh_status"), type="primary"):
        with st.spinner(t("tracking_spinner")):
            ctl.refresh_tracking()
        st.rerun()
    st.caption(t("status_flow_caption"))
    d1, d2, d3, _ = st.columns([1, 1, 1, 3])
    d1.download_button(t("dl_receipt_json"), json.dumps(r["raw"], indent=2),
                       file_name=f"{r['application_id']}.json", mime="application/json")
    d2.download_button(t("dl_receipt_txt"), receipt_text(r),
                       file_name=f"{r['application_id']}.txt", mime="text/plain")
    d3.download_button(t("dl_audit"), audit.build(ctl),
                       file_name="civicpilot_audit.html", mime="text/html")
    with st.expander(t("raw_record"), expanded=True):
        st.code(json.dumps(r["raw"], indent=2), language="json")
    review_table()
    st.button(t("start_over"), on_click=start_over, type="primary")
    st.stop()

if ctl.stage == 4:
    st.header(t("approve_header"))
    for risk in ctl.eligibility_risks:
        st.warning(risk)
    review_table()
    if ctl.otp_pending:
        st.warning(ctl.message or t("otp_default"), icon="⏸️")
        st.caption(t("otp_caption"))
        st.link_button(t("sms_inbox"), f"{config.PORTAL_URL}sms?key={ctl.idem_key}")
        code = st.text_input(t("otp_input"), key="otp_code")
        if st.button(t("verify_otp"), type="primary"):
            with st.spinner(t("otp_spinner")):
                ctl.submit_otp(code)
            st.rerun()
        st.stop()
    if ctl.outcome == "rejected":
        st.error(t("rejected_prefix", msg=ctl.message))
    elif ctl.outcome == "uncertain":
        st.warning(t("uncertain_hint", msg=ctl.message))
        if st.button(t("check_status_btn")):
            ctl.check_status()
            st.rerun()
    elif ctl.outcome == "error" or ctl.message:
        st.error(ctl.message)
    if ctl.outcome != "uncertain":
        ok = st.checkbox(t("confirm_checkbox"), key="confirm")
        c1, c2, c3 = st.columns([1, 1, 4])
        if c1.button(t("submit"), type="primary", disabled=not ok):
            with st.spinner(t("submit_spinner")):
                try:
                    ctl.submit(confirmed=bool(ok))
                except (PermissionError, RuntimeError) as e:
                    ctl.message = str(e)
            st.rerun()
        if c2.button(t("edit")):
            ctl.cancel()
            st.session_state["_pending"] = {"confirm": False}
            st.rerun()
    st.stop()

if ctl.stage == 3:
    st.header(t("review_header"))
    st.success(t("prep_ok"))
    for risk in ctl.eligibility_risks:
        st.warning(risk)
    automation_status()
    review_table()
    a1, a2, c1, c2, _ = st.columns([1.4, 1.2, 1.3, 1, 3])
    a1.download_button(t("dl_audit"), audit.build(ctl),
                       file_name="civicpilot_audit.html", mime="text/html")
    if c1.button(t("continue"), type="primary"):
        ctl.proceed_to_approval()
        st.rerun()
    if c2.button(t("edit")):
        ctl.cancel()
        st.rerun()
    st.stop()

st.header(t("h1"))
st.selectbox(t("service"), list(schema.SERVICES), key="svc", on_change=change_service,
             format_func=lambda s: schema.SERVICES[s].title)
st.text_area(t("request_label"), key="request_text", height=90,
             placeholder=t("request_placeholder"))
st.header(t("h2"))
cols = st.columns(2)
for i, (n, label) in enumerate(svc.fields):
    cols[i % 2].text_input(label, key=f"in_{n}")

with st.expander(t("doc_expander"), expanded=False):
    st.caption(t("doc_caption"))
    doc = st.file_uploader(t("doc_uploader"), type=["pdf", "png", "jpg", "jpeg"], key="doc_up")
    u1, u2, _ = st.columns([1.6, 1.8, 4])
    do_extract = u1.button(t("doc_extract"), disabled=doc is None, type="primary")
    do_sample = u2.button(t("doc_sample"))
    if do_extract or do_sample:
        try:
            if do_sample:
                sample = Path(__file__).parent / "samples" / "marksheet_sample.pdf"
                summary = ctl.ingest_document("marksheet_sample.pdf", sample.read_bytes())
            else:
                summary = ctl.ingest_document(doc.name, doc.getvalue())
            st.session_state["_pending"] = {"svc": ctl.service.id,
                                            **{f"in_{n}": ctl.fields[n] for n in ctl.service.names}}
            st.session_state["doc_summary"] = summary
        except ValueError as e:
            st.session_state["doc_summary"] = {"error": str(e)}
        st.rerun()
    if s := st.session_state.get("doc_summary"):
        if s.get("error"):
            st.error(s["error"])
        else:
            labels = ctl.service.labels
            st.success(t("doc_summary", source=s["source"], mode=s["mode"],
                         fields=", ".join(labels.get(n, n) for n in s["filled"])))

b1, b2, _ = st.columns([1.2, 1.4, 5])
if b1.button(t("analyze"), type="primary"):
    with st.spinner(t("analyze_spinner")):
        ctl.analyze(st.session_state["request_text"], profile_inputs(), st.session_state["svc"])
    if ctl.request:
        push_fields_to_inputs()
    st.rerun()
if ctl.stage >= 1 and b2.button(t("save")):
    ctl.update_fields(profile_inputs())
    st.rerun()

d1, d2, d3, d4, d5 = st.columns(5)
d1.button("Demo: scholarship", on_click=load_demo, args=("scholarship",))
d2.button("Demo: scholarship (missing income)", on_click=load_demo, args=("scholarship", "family_income"))
d3.button("Demo: licence renewal", on_click=load_demo, args=("licence",))
d4.button("Demo: licence (missing PIN code)", on_click=load_demo, args=("licence", "pincode"))
d5.button("Demo: LPG subsidy", on_click=load_demo, args=("subsidy",))

if ctl.message and ctl.stage == 0:
    st.error(ctl.message)

if ctl.stage >= 1:
    st.header(t("h3"))
    st.write(t("selected_service", title=ctl.service.title))
    src = {"profile": t("src_profile"), "request": t("src_request"), "chat": t("src_chat")}
    st.dataframe([{t("field"): ctl.service.labels[n], t("value"): ctl.fields[n] or "-",
                   t("source"): src.get(ctl.sources.get(n, ""), ctl.sources.get(n, "-") or "-"),
                   t("status"): t("status_invalid") if n in ctl.errors
                   else t("status_missing") if n in ctl.missing else t("status_ok")}
                  for n in ctl.service.names], hide_index=True, width="stretch")
    if ctl.missing or ctl.errors:
        st.subheader(t("missing_header"))
        for n in ctl.missing:
            st.warning(t("missing_warn", field=ctl.service.labels[n]))
        for n, m in ctl.errors.items():
            st.error(t("invalid_warn", field=ctl.service.labels.get(n, n), msg=m))
    else:
        st.success(t("all_valid"))
    if ctl.message:
        st.error(ctl.message)
    chat_panel()
    automation_status()
    if ctl.is_valid:
        st.write(t("prepare_hint"))
        label = t("retry") if ctl.auto else t("prepare")
        if setup_problems:
            st.warning(t("setup_blocked"))
        if st.button(label, type="primary", disabled=bool(setup_problems)):
            with st.spinner(t("prepare_spinner")):
                ctl.prepare()
            st.rerun()
