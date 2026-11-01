"""Setup checks shown at app start and by `python3 scripts/doctor.py`.

Each check returns {"ok": bool, "title": str, "detail": str, "fix": str}. No personal data is involved.
"""
import json
import socket
import sys
import urllib.request

import config


def _result(ok, title, detail="", fix=""):
    return {"ok": ok, "title": title, "detail": detail, "fix": fix}


def check_python():
    v = sys.version_info
    ok = v >= (3, 10)
    return _result(ok, "Python version", f"{v.major}.{v.minor}.{v.micro} at {sys.executable}",
                   "" if ok else "Install Python 3.10 or newer (3.11-3.13 recommended).")


def check_chromium():
    """Actually launch Playwright's Chromium once: the only check that catches every install problem."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # pragma: no cover - only when the package itself is missing
        return _result(False, "Playwright package", f"{type(e).__name__}: {e}",
                       "Run: python3 -m pip install -r requirements.txt")
    from core.automation import fix_hint, safe_detail
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            version = browser.version
            browser.close()
        return _result(True, "Playwright Chromium", f"Chromium {version} launches")
    except Exception as e:
        return _result(False, "Playwright Chromium", safe_detail(e),
                       fix_hint(e) or "Run: python3 -m playwright install chromium  (same terminal/venv "
                                      "as the app), then restart the app.")


def portal_health(port=None) -> dict:
    """{'reachable': bool, 'ours': bool}. 'ours' means the answer came from the CivicPilot mock portal."""
    url = f"http://{config.PORTAL_HOST}:{port or config.PORTAL_PORT}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            data = json.loads(r.read() or b"{}")
            return {"reachable": True, "ours": r.status == 200 and data.get("ok") is True}
    except Exception:
        return {"reachable": False, "ours": False}


def port_in_use(port=None) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((config.PORTAL_HOST, port or config.PORTAL_PORT)) == 0


def check_portal(start_error: str = ""):
    h = portal_health()
    if h["ours"]:
        return _result(True, "Mock portal", f"{config.PORTAL_URL}api/health answers OK")
    if start_error or port_in_use():
        return _result(False, "Mock portal",
                       f"Port {config.PORTAL_PORT} is used by another program" +
                       (f" ({start_error})" if start_error else ""),
                       "Set PORTAL_PORT=8777 (any free port) in .env, then restart the app. To see the "
                       f"other program: macOS `lsof -nP -iTCP:{config.PORTAL_PORT} -sTCP:LISTEN`, Windows "
                       f"`netstat -ano | findstr :{config.PORTAL_PORT}`.")
    return _result(False, "Mock portal", f"Nothing is answering on {config.PORTAL_URL}",
                   "Restart the app (it starts the portal automatically).")


def run_all(start_error: str = "", include_portal: bool = True) -> list:
    checks = [check_python(), check_chromium()]
    if include_portal:
        checks.append(check_portal(start_error))
    return checks
