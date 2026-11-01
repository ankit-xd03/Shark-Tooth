# 3-minute demo: checklist and script

Timings measured on a full browser run of this exact flow: prepare ≈ 3 s, submit ≈ 3 s, refresh ≈ 2 s.

## T-15 minutes (on the demo laptop)
1. `source .venv/bin/activate` (Windows: `.\.venv\Scripts\Activate.ps1`)
2. `python3 scripts/doctor.py`: **every line PASS**. If not, apply the printed fix.
3. In `.env` set:
   ```
   DEMO_MODE=true                    # deterministic, even if someone left an API key in .env
   PORTAL_TRACK_DELAY_SECONDS=30     # UNDER REVIEW after 10 s, APPROVED after 30 s
   PORTAL_OTP=false
   ```
4. Run `python3 scripts/benchmark.py --seeds 20` in a second terminal **now** (~90 s), and leave the
   result table on screen.
5. `python3 -m streamlit run app.py`, do one complete dry run, then click **Start over**.
6. Browser: close other tabs and set zoom to 90% so the receipt metrics fit. Record the dry run
   (macOS: Cmd+Shift+5; Windows: Win+Alt+R) as a backup video.

## Script (3:00)
| Time | Click / say |
|---|---|
| 0:00–0:20 | "Government forms are confusing. CivicPilot fills them for you and never submits without your approval." Point at the **mock portal / fictional data** banner and the **Demo mode** banner. |
| 0:20–0:55 | **Demo: scholarship (missing income)** → **Analyze request**. The table shows income *Missing* and no prepare button. Chat: `family income is 3.5 lakh` → all valid. Say: *"Missing data is asked for, never guessed."* |
| 0:55–1:35 | **Authorize agent to prepare the form** → 7/7 fields. Open the **step-by-step gallery**: cookie notice, session-timeout page, each form step. Say: *"The planner decides where to type; values only come from validated data."* |
| 1:35–2:05 | **Continue to approval**. Point out that **Submit** is greyed out. Tick the checkbox → **Submit application** → receipt ID. Say: *"This ID is the portal's own, cross-checked against its records."* |
| 2:05–2:30 | Wait ~10 s → **Refresh status** → UNDER REVIEW. (Click again later for APPROVED.) |
| 2:30–2:50 | Switch to the benchmark terminal: 20 randomized portal layouts × 3 services pass. |
| 2:50–3:00 | Flip the sidebar language to **हिन्दी**. Close: "Hindi/Hinglish, document upload, OTP pause, three services." |

## If a judge asks "show a failure"
- **Rejection:** Start over → **Demo: scholarship** → change income to `900000` → Analyze → prepare. An
  early eligibility warning appears; after submitting, the portal **rejects** it and **no receipt** is shown.
- **Missing browser:** the app's red "Setup problem" box explains the exact fix (we hit this during prep).

## If something breaks live
- Red error box: read its **Technical detail** line aloud. It names the real cause.
- Hard freeze: switch to the backup video. Do not restart Streamlit mid-demo (it takes ~10 s and loses
  the screen).
