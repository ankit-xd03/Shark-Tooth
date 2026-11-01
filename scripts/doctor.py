"""CivicPilot setup doctor: checks everything the demo needs and prints the exact fix for each problem.

Usage (from the civicpilot folder, with the venv active):
    python3 scripts/doctor.py

Checks: Python version, required packages, Playwright Chromium (real launch), portal port, and one
full browser round-trip against a temporary mock portal. Prints field names only, never personal data.
"""
import importlib.metadata as md
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

OK, BAD = "PASS", "FAIL"
failures = 0


def report(ok, title, detail="", fix=""):
    global failures
    failures += 0 if ok else 1
    print(f"[{OK if ok else BAD}] {title}" + (f" - {detail}" if detail else ""))
    if not ok and fix:
        print(f"       Fix: {fix}")


def main():
    print(f"CivicPilot doctor  |  python: {sys.executable}")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"Virtual environment active: {'yes' if in_venv else 'no (fine, but use the SAME python for every step)'}")
    print()

    missing = []
    for pkg in ("streamlit", "playwright", "pypdf", "python-dotenv", "anthropic"):
        try:
            md.version(pkg)
        except md.PackageNotFoundError:
            missing.append(pkg)
    report(not missing, "Python packages", "missing: " + ", ".join(missing) if missing else
           f"playwright {md.version('playwright')}, streamlit {md.version('streamlit')}",
           f"{Path(sys.executable).name} -m pip install -r requirements.txt")
    if missing:
        return

    import config
    from core import automation, preflight
    from portal import server

    c = preflight.check_python()
    report(c["ok"], c["title"], c["detail"], c["fix"])
    chromium = preflight.check_chromium()
    report(chromium["ok"], chromium["title"], chromium["detail"], chromium["fix"])

    h = preflight.portal_health()
    if h["ours"]:
        report(True, f"Port {config.PORTAL_PORT}", "the CivicPilot mock portal is already running there")
    elif preflight.port_in_use():
        report(False, f"Port {config.PORTAL_PORT}", "another program is using it",
               "add PORTAL_PORT=8777 to .env (or stop that program: macOS "
               f"`lsof -nP -iTCP:{config.PORTAL_PORT} -sTCP:LISTEN`, Windows "
               f"`netstat -ano | findstr :{config.PORTAL_PORT}`)")
    else:
        report(True, f"Port {config.PORTAL_PORT}", "free (the app will start the portal there)")

    if not chromium["ok"]:
        print("\nSkipping the browser round-trip until Chromium launches.")
        return
    srv = server.start_in_thread(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        values = {"full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu",
                  "college": "Riverdale Institute of Technology", "course": "B.Tech Computer Science",
                  "academic_year": "3", "family_income": "350000", "cgpa": "8.4"}
        res = automation.fill_form("scholarship", values, "doctor-check", base)
        report(res["ok"], "Browser round-trip (fills the demo scholarship form on a temporary portal)",
               f"{len(res['completed'])}/7 fields filled" + ("" if res["ok"] else ": " + " ".join(res["errors"])))
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
    print()
    print("All checks passed. Start the app with: python3 -m streamlit run app.py" if failures == 0
          else f"{failures} check(s) failed. Apply the fix shown, then run this again.")
    sys.exit(1 if failures else 0)
