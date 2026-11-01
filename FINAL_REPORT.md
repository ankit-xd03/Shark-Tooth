# CivicPilot AI — Final Report (what changed, and how to explain it to judges)

Everything below is written so a student can explain the project in simple language. Where a technical
idea appears, there is an everyday Indian analogy in italics.

---

## (a) File-by-file summary of every change

### `app.py` — the shop counter (the Streamlit UI)
*Think of this as the counter at a CSC / e-Mitra shop: whatever the citizen needs to see or press lives here.*
- **Step-by-step screenshot gallery**: every move the browser agent makes is kept as a photo in memory. The
  gallery shows the cookie notice, the "session expired" page and each form step, with the *names* of the
  fields filled — never the values.
- **Chat panel**: if something is missing, CivicPilot now asks one question at a time ("What is your annual
  family income?") and the citizen can just reply in words. The form stays as a fallback.
- **Live tracking card** on the receipt screen with a real "Refresh status" button that sends the browser
  to the portal's tracking page.
- **Document upload**: a paper clip section that reads a marksheet / income certificate / licence copy
  (text PDFs work with no AI key), fills the fields, and shows each value's source ("from marksheet.pdf").
- **Language toggle** (English / हिन्दी) for all key strings, plus a stage progress bar in the sidebar.
- **Audit report download**: one HTML file with the timeline, the trace table, the screenshots, the
  validation summary and the outcome — no personal values in it.
- New demo button for the **LPG subsidy** service; demo profile/request data for all three services.

### `config.py` — the settings cupboard
- Unchanged apart from documentation: model IDs (`claude-haiku-5-5`, `claude-sonnet-5-5`,
  `gemini-2.5-flash`) were **verified against the providers' docs** before being kept as defaults.

### `core/schema.py` — the rule book (validators for each service)
*Like the clerk's checklist: what a valid name, PIN code or income looks like.*
- **New third service "subsidy"** (LPG connection subsidy claim) with its own fields and validators
  (10-digit consumer ID, PMUY/General connection type, IFSC, account last-4, annual income). This is the
  proof that the registry design works: adding a service touched only `schema.py`, `portal/server.py`
  (plus hints, demo data and tests).
- Devanagari digits (०-९) accepted in income/year/CGPA; names may now be in Hindi script.

### `core/extractor.py` — the interpreter (understands what the citizen wrote)
*Like the helpful shopkeeper who listens in English, Hindi or Hinglish and fills the form for you.*
- Hinglish + Hindi understanding: "Mujhe scholarship ke liye apply karna hai, income 3.5 lakh hai, CGPA 8.4"
  and full Devanagari sentences (छात्रवृत्ति, आय, लाख, मेरा नाम, तीसरे साल) are parsed in demo mode.
- **`parse_reply` / `chat_extract`**: parse one targeted answer from a chat reply (regex first, LLM when a
  key exists, validators always).
- Document-oriented label variants ("Name:", "Course:", "Year of Study:") and subsidy field extraction.
- LLM prompts now say the message may be English/Hindi/Hinglish.

### `core/planner.py` — the navigator (decides which box to click or type in)
*Like an auto driver who knows every gali of an old city.*
- Hint weights tuned and extended so the planner survives randomized portals: label synonyms ("Candidate
  Name", "Study Year", "Class of Licence", "as per records"), dropdown wording variants ("Year 3"),
  decoy fields and decoy buttons, and an "I Acknowledge" instructions page (new obstacle).
- Benchmark-driven fixes: the plan never clicks anything that looks like submit/back/edit/pay/logout.

### `core/automation.py` — the driver (actually presses the keys in the browser)
*The person who physically fills the form at the counter.*
- **Screenshots after every step** (JPEG, in memory only).
- **Self-healing**: if the portal rejects a format ("Use DD-MM-YYYY with hyphens"), the agent re-formats
  the *same* validated value (never invents a new one), retries that field at most twice, and writes the
  correction into the trace. A DD-MM-YYYY portal variant exists to prove it.
- **Tracking**: opens the portal tracking page, reads the status, and refuses a mismatched reference.
- **Eligibility reading**: opens the portal's eligibility page and extracts the rules (regex in demo mode,
  LLM when available).
- **OTP completion**: after the user types the code in the app, the agent types it into the portal — it
  never reads or guesses the code itself, and the OTP page never contains the code.
- Review-page verification now accepts the value in the exact form the agent typed (so corrected dates do
  not fail the check).

### `core/controller.py` — the manager (the stage machine with all the gates)
*The supervisor who stamps the file only after every check passes.*
- **Chat**: `chat_question()` / `chat_reply()` with a question bank; values are validated by the same
  rule book; the log records only "chat reply filled income" (no values).
- **Eligibility pre-check**: before filling, the manager reads the rules and warns early ("income exceeds
  the limit; likely rejection") but still lets the user proceed.
- **OTP pause**: submission stops, control returns to the user; `submit_otp()` continues only with a
  user-typed 6-digit code.
- **Tracking refresh** and history status updates; document ingestion with per-value source labels;
  audit context (last submit trace) retained for the report.

### `core/documents.py` (new) — the photocopier that reads papers
- Text PDFs are read locally with `pypdf` and parsed with the existing extractors (works in demo mode).
- Images/scans go to the vision LLM (all three providers supported); without a key the app says clearly
  that images need one.
- Every value keeps its source filename and passes the same validators as typed input.

### `core/audit.py` (new) — the file's certified copy
- Builds a single self-contained HTML audit report: timeline, trace tables, screenshots, corrections,
  validation summary, outcome. No field values.

### `core/store.py` — the register book
- New `update_status()` so the tracking card can move a row from ACCEPTED to APPROVED/UNDER REVIEW.
- Still no personal data in the register.

### `portal/server.py` — the fake government office (deliberately awkward)
*The "sarkari office" with the notice board, token system and that one form that needs a different pen.*
- **Seeded layout randomizer**: label synonyms, shuffled field order, randomized element ids, decoy fields
  and buttons ("Print Form", "Help"), extra "Important Instructions" pages, dropdown wording variants
  ("Year 3" instead of "3rd Year"), and a DD-MM-YYYY date variant — all deterministic per seed.
- **Tracking**: `/track` page + `/api/track` with SUBMITTED → UNDER REVIEW → APPROVED progression.
- **Eligibility**: a rules page per service + `/api/eligibility`.
- **OTP wall** (optional, `PORTAL_OTP=true`): Final Submit shows an OTP challenge; the code appears only
  on the simulated `/sms` inbox page; wrong codes are rejected with a message.
- **Third wizard** for the LPG subsidy service with its own eligibility rules (PMUY only, income ≤ 2.5 lakh).

### `scripts/benchmark.py` (new) — the practice test series
- Runs N seeded layouts per service in demo mode (or with an LLM key), prints a success-rate table with
  failure reasons, and honestly splits tuning seeds (1–10) from **held-out seeds (11+)**.
- Final honest score: **100% (90/90 journeys) over 30 seeds × 3 services, including full submission**,
  with cookie/timeout obstacles on.

### `scripts/make_samples.py` (new) + `samples/` — the fake documents
- Three fictional PDFs (marksheet, income certificate, licence copy) generated with zero dependencies.

### `tests/` — the examiners
- 113 passing tests + 3 auto-skipped live-LLM tests (count as of the setup-hardening update) (they run only when a real API key exists).
- New: screenshots, chat journey (UI-level), fixed-seed randomized portal, self-healing, tracking,
  eligibility, OTP pause (including "the code never appears on the OTP page or in the log"), subsidy
  end-to-end, Hindi/Hinglish parsing, documents, language toggle, audit button, subsidy demo button.

### `requirements.txt`, `.env.example`, `README.md`
- Added `pypdf>=5.0`; new env knobs documented (`PORTAL_OTP`, `PORTAL_TRACK_DELAY_SECONDS`, `PORTAL_SEED`,
  `PORTAL_DATE_HYPHENS`); README fully rewritten (architecture, safety design, demo script, test-to-spec
  table, assumptions, trade-offs, honest limitations).

---

## (b) Exact commands to run it on macOS

```bash
cd civicpilot
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium   # separate download: pip does NOT install the browser
python3 scripts/doctor.py                # every line must say PASS
python3 -m pytest -q
python3 -m streamlit run app.py
```
Windows (PowerShell) steps are in the README.
Then open http://localhost:8501. No API key is needed (demo mode). Optional extras:
```bash
python3 scripts/benchmark.py --seeds 20        # randomized-portal robustness benchmark
PORTAL_OTP=true python3 -m streamlit run app.py # show the OTP pause demo
```

---

## (c) 3-minute demo script (exact clicks)

**0:00–0:20 — Hook.** "Government portals are old, confusing and in the way. CivicPilot is an agent that
fills them for you — and it never submits anything without pressing your approval." Point at the banner:
*local mock portal, fictional data only.*

**0:20–0:50 — Chat instead of forms.** Click **"Demo: scholarship (missing income)"** → **"Analyze
request"**. The summary table shows income missing. In the chat panel type: `family income is 3.5 lakh`.
The app validates it instantly. Talking point: *"missing data is asked for, never guessed."*

**0:50–1:30 — The agent works.** Click **"Authorize agent to prepare the form"**. Open the **step-by-step
gallery**: screenshots of the cookie notice, the session-timeout page, and each form step — with field
names only. Talking point: *"the planner decides where to type; values always come from the validated
profile."*

**1:30–2:10 — Approval and receipt.** **"Continue to approval"** → tick the checkbox → **"Submit
application"**. Receipt shows the portal's real application ID, verified against the portal's own record.
Click **"Refresh status"**: the browser opens the tracking page and the live status appears
(SUBMITTED → UNDER REVIEW → APPROVED). Talking point: *"after submission, the agent keeps working for
you — and every claim is verified against the portal."*

**2:10–2:40 — Robustness (the wow).** Run `python3 scripts/benchmark.py --seeds 20` *before* the demo (it
takes ~90 s) and just switch to that terminal to show the table: 20 randomized versions of the portal (shuffled fields, decoy buttons, different wording) pass
end-to-end. Talking point: *"we test our agent the way real portals change — randomly."*

**2:40–3:00 — Range.** Click **"Demo: LPG subsidy"** (third service with its own wizard and rules), flip
the sidebar language to **हिन्दी**, and mention: *"the same agent handles Hindi/Hinglish input, document
uploads, and pauses safely for OTPs — try it with PORTAL_OTP=true."*

---

## (d) Likely judge questions and strong answers

**Q: How do you guarantee it never submits without permission?**
A: The submit click lives in one function that the controller only reaches at the "Awaiting Approval"
stage with `confirmed=True` from an explicit checkbox. The planner cannot click submit-class buttons at
all — an LLM plan that tries is thrown away and rules take over. There are tests for each of these doors.

**Q: The LLM could hallucinate values. So what does it actually control?**
A: Only *where* to type and what to click next — never *what* to type. Values come from the validated
profile. A bad LLM plan is rejected in code and falls back to a rule-based planner; a failed LLM call
falls back to demo mode with a visible warning.

**Q: What if the portal shows a CAPTCHA or OTP?**
A: We never bypass them. We demonstrate the pattern with an OTP wall: the agent detects it, pauses, and
the user types the code from a simulated SMS inbox into the app; the agent only fills it in. Tests assert
the code never appears on pages the agent reads or in logs.

**Q: How do you know your agent isn't overfit to your own mock portal?**
A: We built a seeded randomizer that reshuffles labels, field order, ids, dropdowns, decoy controls and
interstitials, then ran 30 seeds per service — 20 of them held out from tuning — at 100% with the
deterministic planner. The benchmark prints failures honestly so the number is checkable.

**Q: What stops duplicate submissions if the browser crashes mid-submit?**
A: Every draft carries an idempotency key; the portal records an application once per key, re-running is
safe, and an unreadable result is marked "uncertain" — the app checks the portal's record instead of
retrying automatically.

**Q: Why does verification of the receipt matter?**
A: A receipt on screen is just text; we parse it *and* cross-check it against the portal's status API by
application ID. If they disagree, the app says "uncertain" and never shows a fabricated success.

**Q: Where do the AI features actually earn their keep?**
A: Routing ambiguous requests, extracting fields from free-form Hinglish and from documents, planning on
pages the rules can't score, and reading eligibility pages. All of them degrade to deterministic paths
with no key — which is also how we run all 113 tests.

**Q: What data do you store?**
A: History keeps service, application ID, status and timestamp. Logs and traces keep field *names*, not
values. Screenshots stay in session memory unless the user downloads the audit report.

**Q: Why two browser sessions instead of one?**
A: A session kept open while the human reviews is exactly what session timeouts model — the portal may
expire it and the draft may drift. Replaying in a fresh session with full re-verification plus the
idempotency key is safer and crash-proof. (Documented trade-off in the README.)

**Q: What's real vs mock here?**
A: The browser automation, planner, validation, self-healing, tracking and safety gates are all real code
paths tested by 113 automated tests. The government portal, its data and the SMS inbox are mocks so that
no real system is ever touched — by design, not by accident.

---

## (e) Honest remaining limitations

1. **Live LLM calls are not exercised in the automated suite** (no API key in CI). `tests/test_live_llm.py`
   covers extraction, routing and planning for real when a key is set; everything else is mocked.
2. The **vision/document path for images** is implemented for all three providers but is untested live
   without a multimodal key; demo mode only reads text PDFs and clearly says so.
3. The **mock portal is ours** — real portals may add CAPTCHAs, logins, iframes, file downloads or
   JavaScript-heavy UIs that need more planner work.
4. **Hindi coverage is curated** (लाख, आय, छात्रवृत्ति, Devanagari digits, common ordinals, name
   patterns); broader Hindi needs the LLM path.
5. Screenshots and traces live in **session memory**; they are lost when the tab closes (download the
   audit report to keep one).
6. The benchmark score applies to **seeded variants of our own portal**; it measures planner robustness,
   not the open internet.
7. Hindi UI strings cover the main journey; a few long captions remain English.
8. Two browser sessions per application (documented trade-off) instead of one persistent session.

---

## (f) Setup-hardening update

- **Root cause of "The portal could not be reached or the browser failed":** that text hid the real
  exception. The most common cause is that Playwright's Chromium was never downloaded
  (`python3 -m playwright install chromium` is separate from `pip install`).
- `core/automation.py`: browser failures now show `<ExceptionType>: <first line>` plus a plain fix
  (`safe_detail()` / `fix_hint()`). Applicant values, emails, API keys, URL query strings and the local
  username are removed. A timeout no longer claims "Nothing was submitted" (that could be false after the
  submit click).
- `core/preflight.py` + `app.py`: startup check (real Chromium launch, portal health and port owner). A red
  "Setup problem" box with the fix, a "Re-check setup" button, and the prepare button stays disabled
  until the setup is fixed. A port conflict no longer crashes the app on start.
- `scripts/doctor.py`: one-command setup check with PASS/FAIL and fixes.
- `app.py`: a chat answer now also fills the profile box. Before, "Save & re-validate" after a chat answer
  silently wiped it. `use_container_width` replaced by `width="stretch"` (deprecated in Streamlit);
  `streamlit>=1.50`.
- `portal/server.py`: `/api/health` identifies the CivicPilot portal, so another program on the port is
  not mistaken for it.
