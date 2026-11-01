# CivicPilot AI: Autonomous Public Service & Bureaucracy Execution Agent

A conversational agent that completes **public-service applications** (student scholarship, driving-licence
renewal, LPG-connection subsidy claim) by driving a real browser (Playwright) through a **legacy-style mock
government portal**: server-rendered wizards, blocking cookie notices, session timeouts, coded dropdowns,
decoy buttons, an optional OTP wall and a tracking page. It fills forms, handles UI obstacles, recovers from
format errors, returns a verified receipt, and then **tracks** the application live. Nothing is submitted
without the user's explicit approval, and all data is fictional.

## What the agent does
1. **Understands** a plain-English, Hindi or Hinglish request ("Mujhe scholarship ke liye apply karna hai,
   income 3.5 lakh hai, CGPA 8.4") and routes it to a service (keywords, or the LLM if configured).
2. **Extracts** structured fields (LLM, or a deterministic parser in demo mode) — also from uploaded
   documents (text PDFs in demo mode; scans/images via a vision LLM) — and validates them. Missing or
   invalid values are **reported, never invented**: the chat panel asks one targeted question at a time
   until the data is complete.
3. **Reads the portal's eligibility page** through the browser and warns early ("income exceeds the limit;
   likely rejection") while still letting the user decide.
4. **Navigates the portal** with an observe → plan → act loop: it reads visible controls, dismisses
   obstacles (cookie notice, session timeout, instruction interstitials), fills each step, and
   **self-heals** when the portal demands a different format (e.g. DD-MM-YYYY dates) by re-formatting the
   *same validated value* — never a new one.
5. Stops at the review page and **verifies** every entered value against the page text.
6. After explicit approval, clicks the final submit, reads the **real receipt**, cross-checks it against
   the portal record, pauses for an **OTP** when the portal demands one (the user types the code; the agent
   never reads or guesses it), and shows a **live tracking card** (SUBMITTED → UNDER REVIEW → APPROVED).

## Highlights for judges
- **Screenshot trace (P1-A):** every agent step keeps an in-memory screenshot; the UI shows a step-by-step
  gallery (page type, field names filled, what was clicked). Nothing hits the disk unless you download the
  **audit report**.
- **Chat follow-up (P1-B):** complete an application purely by answering chat questions.
- **Randomized robustness benchmark (P1-C):** `python3 scripts/benchmark.py` reseeds the portal's labels,
  field order, ids, buttons, dropdowns, decoys and interstitials, and prints an honest success table with a
  held-out seed range. Demo-mode planner scores **100% over 30 seeds per service** (seeds 11–30 held out).
- **Tracking (P1-D):** the agent really drives the browser to the portal's tracking page on "Refresh status".
- **Trilingual UI (P2-J):** the whole interface chrome — headings, buttons, stage names, warnings, tracking
  and download labels — switches between **English, हिन्दी and Hinglish** from the sidebar picker; requests
  could already be typed in any of the three.
- **Self-healing (P2-F), eligibility pre-check (P2-G), OTP pause (P2-H), third service (P2-I),
  document upload (P2-E), audit report + structured logging (P3-L), auto-skipped live-LLM tests (P3-M).**

## Architecture
```
app.py                Streamlit UI (stages, chat panel, screenshot gallery, tracking card, downloads)
config.py             Environment-based settings (no secrets in code)
core/schema.py        Service registry: fields, validators, formatters (scholarship, licence, subsidy)
core/extractor.py     Routing + extraction (LLM with deterministic fallback), chat reply parsing
core/planner.py       Page planner: LLM (validated) with a rule-based fallback; safety filters
core/automation.py    Playwright observe/act loop, screenshots, self-healing, tracking, OTP completion
core/controller.py    Stage machine + approval / idempotency / OTP gates + eligibility pre-check
core/documents.py     Document intake: pypdf text in demo mode, vision-LLM for images
core/i18n.py          UI translations: English, हिन्दी, Hinglish (chrome only; portal stays English)
core/audit.py         One-file HTML audit report (timeline, trace, screenshots, outcome)
core/store.py         SQLite history (service, application_id, status, submitted_at — no personal data)
portal/server.py      Mock legacy portal: 3 wizards, obstacles, seeded randomizer, eligibility, OTP,
                      SMS inbox, tracking, status APIs
scripts/benchmark.py  Seeded robustness benchmark with honest held-out reporting
scripts/make_samples.py  Regenerates the fictional sample PDFs in samples/
tests/                Unit, planner, browser, feature and UI journey tests (+ live-LLM, auto-skipped)
```
The portal starts automatically in a background thread (default `http://127.0.0.1:8765/`).

### Mock portal endpoints (backend)
| Method + path | Purpose |
|---|---|
| `GET /api/health` | `{"ok": true, "service": "civicpilot-mock-portal"}`, used by the startup check and the doctor |
| `GET /svc/<service>/?key=<k>` | Start a wizard (`scholarship`, `licence`, `subsidy`); `key` is the draft's idempotency key |
| `POST /svc/<service>/step/<n>?key=<k>` | Submit wizard step *n* (server-side validation, per-field errors) |
| `POST /svc/<service>/submit?key=<k>` | Final submit (idempotent per key); returns the receipt or a rejection page |
| `POST /svc/<service>/otp?key=<k>` | OTP challenge (only with `PORTAL_OTP=true`) |
| `GET /svc/<service>/eligibility` | Human-readable eligibility rules page |
| `GET /api/status?key=<k>` | Portal record for a draft key (used to verify receipts) |
| `GET /track?ref=<id>`, `GET /api/track?ref=<id>` | Tracking page / JSON status for an application ID |
| `GET /api/eligibility?service=<service>` | Eligibility rules as JSON |
| `GET /sms?key=<k>` | Simulated SMS inbox showing the OTP |

### Interface languages (how to extend)
`core/i18n.py` holds every UI string as `TRANSLATIONS[key][lang]` for `en`, `hi` and `hinglish`, plus
`STAGE_NAMES` per language. `app.py` reads the sidebar picker (stored as the language code in
`st.session_state["lang"]`) through a one-line wrapper `t(key, **fmt)`; `t` falls back to English and then
to the key itself, and `{placeholders}` are filled with `str.format`.
- **Add a string:** give it a key with `en`/`hi`/`hinglish` text in `core/i18n.py` and call `t(key)` in
  `app.py`. `tests/test_i18n.py` enforces non-empty text for every language and identical `{placeholders}`
  across languages.
- **Add a language:** add its code and display name to `LANGUAGES`, fill the new text for every key and for
  `STAGE_NAMES`, and add the code to the loop in `tests/test_i18n.py`.
- **Deliberately not translated:** field labels from `core/schema.py`, everything the mock portal displays,
  controller/agent messages, log lines and values sent to the portal — the portal plays a legacy system with
  its own fixed language, and submissions must match its format. Demo buttons stay English because tests and
  the demo script click them by label.

### The mock portal is deliberately hard
Blocking cookie notice, a session-timeout page, optional instruction interstitials, auto-generated element
ids, decoy fields ("Father's / Husband's Name", "Aadhaar Enrolment Number") and decoy buttons ("Print Form",
"Help"), labels that differ from the assistant's field names, coded dropdowns ("3rd Year" is value `Y3`),
a three-step wizard per service, server-side validation, eligibility rules, and an idempotent submit API.
`PORTAL_CHAOS=false` turns the obstacle pages off; `PORTAL_SEED=<n>` reseeds the random layout for demos;
`PORTAL_DATE_HYPHENS=true` forces the DD-MM-YYYY portal variant; `PORTAL_OTP=true` enables the OTP wall
with the `/sms` simulated inbox.

### Safety design (the non-negotiables)
1. **Nothing is submitted without explicit approval**: the final-submit control can only be clicked by
   `submit_application`, which the controller allows only from the Awaiting Approval stage with
   `confirmed=True` from a UI checkbox.
2. **The LLM/planner never supplies values** and can never click final-submit/confirm/pay/delete/logout/
   back/edit controls. LLM plans are validated in code; anything invalid falls back to the rule planner.
3. **Missing or invalid data is reported, never guessed** — in the form, in chat, and in the browser.
4. **Requests outside the portal origin are aborted and stop the run**; missing elements stop the run.
5. **Idempotency**: a fresh key per draft/revalidation prevents duplicate submissions; an unreadable result
   is "uncertain" and is resolved by checking the portal record — never auto-retried.
6. **Receipts come from the portal's actual response**, verified against its status record.
7. **Logs, traces, history and the audit report contain field names, never values.** Fictional data only;
   the agent refuses real government sites by construction (it only ever talks to the local mock).
8. **CAPTCHAs/OTPs/logins are never bypassed**: the OTP wall pauses the run and hands control to the user.
9. **Runs end-to-end with no API key** (demo mode) and degrades gracefully if an LLM call fails.

## Setup
Prerequisites: Python 3.10–3.13 and internet access for the one-time downloads. No API key is needed.

> **The step people miss:** `pip install` installs the Playwright *library* only. The Chromium
> *browser* it drives is a separate ~150 MB download (`python3 -m playwright install chromium`). It must be
> run with the **same Python/venv** that runs the app. If it is skipped, the app shows a red
> "Setup problem: Playwright Chromium" box at the top and the prepare button stays disabled.

### macOS (Terminal)
```bash
cd civicpilot
python3 -m venv .venv
source .venv/bin/activate                 # the prompt now starts with (.venv)
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium    # downloads the browser (one time)
cp .env.example .env                      # optional; leave the keys empty for demo mode
python3 scripts/doctor.py                 # every line must say PASS
python3 -m streamlit run app.py           # opens http://localhost:8501
```

### Windows (PowerShell)
```powershell
cd civicpilot
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1              # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium     # downloads the browser (one time)
copy .env.example .env                    # optional; leave the keys empty for demo mode
python scripts\doctor.py                  # every line must say PASS
python -m streamlit run app.py            # opens http://localhost:8501
```
On Windows, type `python` wherever this README says `python3`.

**Every new terminal:** activate the venv again (`source .venv/bin/activate` or
`.\.venv\Scripts\Activate.ps1`) before running the app or the tests.

With no key (or `DEMO_MODE=true`) the app runs in **demo mode** with a visible banner; every LLM failure
falls back to the deterministic path and says so. `pypdf` is included for text-PDF extraction; scanned
documents and images need a vision-capable LLM key.

### Built-in setup checks
- `python3 scripts/doctor.py` checks the Python version, packages, a **real Chromium launch**, port
  `PORTAL_PORT` (default 8765) and one full browser round-trip on a temporary portal. Each failure prints
  the exact fix.
- The app runs the same Chromium and portal checks at startup. Problems appear as a red **Setup
  problem** box with the fix, and a **Re-check setup** button re-runs them after you fix things (no restart
  needed for the browser install).
- Browser errors in the app now show the real exception type and its first line (for example
  `Error: BrowserType.launch: Executable doesn't exist at ~/Library/Caches/ms-playwright/...`). Applicant
  values, emails, API keys, URL query strings and your home-folder username are removed from that text.

## LLM providers (all optional)
| Provider | `.env` settings |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY=...` (defaults: `claude-haiku-5-5` extraction, `claude-sonnet-5-5` navigation — IDs verified against provider docs) |
| Google Gemini | `GEMINI_API_KEY=...` (default `gemini-2.5-flash`) |
| Groq / OpenRouter / OpenAI | `OPENAI_API_KEY=...`, `OPENAI_BASE_URL=...`, `LLM_MODEL=<model>` |
| Ollama (local) | `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=<pulled model>` |

`LLM_MODEL` overrides both roles; `LLM_AGENT_MODEL` overrides navigation only. Model names change — check
the provider docs.

## Run
```bash
python3 -m streamlit run app.py     # opens http://localhost:8501
python3 -m portal.server            # optional: run the mock portal on its own
python3 scripts/benchmark.py        # seeded robustness benchmark (demo mode; ~4-5 s per seed)
python3 scripts/doctor.py           # setup check: Chromium, port, one browser round-trip
```

## 3-minute demo script
1. **Home → "Demo: scholarship (missing income)" → Analyze request.** The summary shows every field with
   its source; income is flagged missing. Open the **chat panel** and type *"family income is 3.5 lakh"* —
   the app validates and continues. (Alternative: upload the sample marksheet PDF.)
2. **"Authorize agent to prepare the form".** Open the **step-by-step gallery**: the cookie notice, the
   session-timeout interstitial and each form step appear as screenshots with field names (never values).
3. **"Continue to approval"** → tick the approval checkbox → **"Submit application"**. The receipt shows
   the portal's real application ID, verified against the portal record.
4. **"Refresh status"** — the agent opens the portal tracking page in a browser and shows the live status
   (SUBMITTED → UNDER REVIEW after a third of `PORTAL_TRACK_DELAY_SECONDS` → APPROVED after all of it; default
   90 s. For a live demo put `PORTAL_TRACK_DELAY_SECONDS=30` in `.env`: UNDER REVIEW after 10 s, APPROVED after 30 s).
5. Extra wow: **"Demo: LPG subsidy"** (third service, zero changes outside the registry), the **Hindi
   toggle** (🌐 in the sidebar), `PORTAL_OTP=true` for the OTP pause with the simulated SMS inbox, and
   `PORTAL_SEED=7` to show a randomized portal layout. Rejections are genuine: try income 900000 or a
   licence expired more than a year ago — the eligibility pre-check warns *before* the portal does.

## Test
```bash
python3 -m pytest -q        # 113 pass + 3 live-LLM tests auto-skipped without a key (~2 min; needs Chromium)
```
| Spec / invariant | Covered by |
|---|---|
| Complete application through obstacles | `test_fill_form_completes_all_fields_through_obstacles`, `test_full_ui_journey` |
| Missing field never invented | `test_missing_field_not_invented`, `test_cannot_prepare_with_missing_fields`, `test_missing_field_blocks_preparation`, `test_chat_reply_invalid_value_is_not_guessed` |
| Invalid input reported per field | `test_invalid_input_scholarship`, `test_invalid_input_licence`, `test_subsidy_validation_rules`, `test_portal_validation_error_is_reported_per_field` |
| Explicit approval gate | `test_submission_requires_explicit_approval`, `test_no_submit_before_approval_stage`, `test_planner_never_picks_final_submit` |
| Unsafe LLM plans rejected | `test_llm_cannot_click_final_or_blocked`, `test_bad_llm_plan_falls_back_to_rules` |
| Off-origin navigation blocked | `test_unexpected_url_blocked`, `test_redirect_off_origin_is_blocked` |
| Missing elements stop the run | `test_missing_elements_stop_instead_of_guessing`, `test_portal_down_stops_safely` |
| Browser failure shows real cause, no PII/keys | `tests/test_setup.py` (missing Chromium, portal down, port conflict, redaction) |
| Startup setup check in the UI | `test_missing_browser_shows_setup_error_and_blocks_preparation` |
| Chat answer survives Save & re-validate | `test_chat_answer_reaches_profile_and_survives_save` |
| Verified receipt, no fabrication | `test_end_to_end_submit_and_receipt`, `test_otp_complete_automation_direct` |
| Idempotency / uncertain result | `test_duplicate_key_is_idempotent`, `test_uncertain_result_is_checked_not_retried` |
| Screenshot trace (P1-A) | `test_trace_includes_screenshot_per_step`, `test_trace_includes_screenshot_of_submit_result` |
| Chat follow-up (P1-B) | `test_chat_only_journey_end_to_end`, `test_chat_panel_completes_missing_field_journey` |
| Randomized portal (P1-C) | `test_randomized_portal_layout_fixed_seed_set` (seeds 2/9/14 × 3 services), `scripts/benchmark.py` |
| Tracking (P1-D) | `test_track_application_reads_status_via_browser`, `test_refresh_tracking_updates_history` |
| Self-healing (P2-F) | `test_self_healing_hyphen_date_portal`, `test_self_healing_accepts_same_source_value_only` |
| Eligibility pre-check (P2-G) | `test_eligibility_precheck_warns_but_allows`, `test_read_eligibility_all_services` |
| OTP pause (P2-H) | `test_otp_pause_hands_control_to_user` (code never on the OTP page, never in the log) |
| Third service (P2-I) | `test_subsidy_end_to_end_accepted`, `test_subsidy_end_to_end_rejects_general_connection` |
| Hindi/Hinglish (P2-J) | `test_hinglish_request_extracts_and_routes`, `test_devanagari_request_extracts_and_routes`, `test_language_toggle_switches_ui_strings` |
| Documents (P2-E) | `test_sample_marksheet_pdf_fills_scholarship`, `test_image_without_llm_key_is_rejected` |
| Live LLM (P3-M) | `tests/test_live_llm.py` — real calls, auto-skipped without a key |

## Assumptions
- Mock eligibility: scholarship income ≤ INR 8,00,000 and CGPA ≥ 6.0; licence renewal within 365 days of
  expiry (applicant 18+); subsidy income ≤ INR 2,50,000 on a PMUY (Ujjwala) connection.
- Tracking status progresses with time: SUBMITTED → UNDER REVIEW → APPROVED (`PORTAL_TRACK_DELAY_SECONDS`,
  default 90).
- Profile values take priority; extracted values (request, chat, document) only fill blanks; the service
  named in a request or document overrides the picker.
- UI strings switch between English and Hindi; field values and portal submissions stay in the portal's
  expected format.

## Design trade-off: two browser sessions (P3-K)
Preparation and submission each open a fresh browser session. We considered keeping one persistent session
between the two, but keeping a Chromium (with a live, pre-filled government draft) open while the user is
away from the keyboard is exactly the situation a session-timeout page models: the portal may expire the
session, another tab could alter it, and a long-lived authenticated context is a liability. Instead, the
submit run **replays the whole flow in a fresh session**, re-verifies every value on the review page, and
the per-draft **idempotency key** makes even a crash safe (the portal records the application once). The
approval gate is unchanged: the click happens only after `confirmed=True` at the Awaiting Approval stage,
in a session proven to be on the review page with unchanged values.

## Known limitations (honest)
- **Live LLM paths are tested with mocks, not live APIs** (no key in CI). `tests/test_live_llm.py` runs for
  real when a key is set; the automated suite exercises the rule-based planner and parser.
- The portal is a mock; real portals add CAPTCHAs, logins and PDF downloads, which this prototype pauses on
  rather than bypasses (OTP demonstrates the pattern).
- The chat and extractors handle a curated Hinglish/Hindi vocabulary (लाख, आय, छात्रवृत्ति, Devanagari
  digits, common ordinals); free-form Hindi beyond that needs the LLM path. The trilingual UI covers interface
  chrome only; portal pages and controller messages remain in English.
- Image documents and scanned PDFs need a vision LLM key; demo mode reads text PDFs only.
- The LLM vision path is implemented for all three providers but, like other live paths, is not exercised
  in the automated suite without keys.
- Screenshots live in session memory; closing the browser tab discards them (download the audit report to
  keep one).
- The benchmark's success rate is for the deterministic planner on seeded variants of our own mock portal;
  real-world legacy portals are wilder.
- History stores only service, application ID, status and timestamp (privacy by construction), so it cannot
  show a full application list view.

## Troubleshooting
Start with `python3 scripts/doctor.py`; it pinpoints all of the cases below.

| You see | Cause | Fix |
|---|---|---|
| `Executable doesn't exist at …ms-playwright…` | Chromium never downloaded, or downloaded for a different Python/venv | Activate the venv, run `python3 -m playwright install chromium`, click **Re-check setup** |
| `Host system is missing dependencies` (Linux) | OS libraries missing | `python3 -m playwright install --with-deps chromium` |
| `ERR_CONNECTION_REFUSED` | Portal not running | Restart the app; `curl http://127.0.0.1:8765/api/health` should print `{"ok": true, ...}` |
| "Port 8765 is used by another program" | Port conflict | Add `PORTAL_PORT=8777` to `.env` and restart. To find the program: macOS `lsof -nP -iTCP:8765 -sTCP:LISTEN`, Windows `netstat -ano \| findstr :8765` |
| `TimeoutError: … Timeout 8000ms exceeded` | Slow machine | Raise `BROWSER_TIMEOUT_MS` (e.g. 20000) in `.env` |
| `ModuleNotFoundError: streamlit` / `playwright` | venv not active in this terminal | Activate it, or `python3 -m pip install -r requirements.txt` |

- *Timeouts on slow machines*: raise `BROWSER_TIMEOUT_MS`.
- *Watch the agent work*: set `PLAYWRIGHT_HEADLESS=false` and `PLAYWRIGHT_SLOW_MO_MS=400`.
- *Regenerate the sample documents*: `python3 scripts/make_samples.py`.
