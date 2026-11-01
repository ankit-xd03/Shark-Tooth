"""Audit report builder (P3-L): one self-contained HTML file with the timeline, trace, screenshots,
validation summary and outcome. Contains no field values beyond what the user already saw on screen.
"""
import base64
import html
from datetime import datetime, timezone


def _shot_img(shots, i, label):
    if i >= len(shots) or not shots[i]:
        return ""
    b64 = base64.b64encode(shots[i]).decode()
    return (f'<figure><img src="data:image/jpeg;base64,{b64}" alt="{html.escape(label)}">'
            f'<figcaption>{html.escape(label)}</figcaption></figure>')


def _trace_section(title, res):
    e = html.escape
    if not res or not res.get("trace"):
        return ""
    shots = res.get("shots") or []
    body_rows = ""
    for i, row in enumerate(res["trace"]):
        body_rows += (f"<tr><td>{e(str(row.get('step', '')))}</td><td>{e(str(row.get('planner', '')))}</td>"
                      f"<td>{e(str(row.get('page', '')))}</td><td>{e(str(row.get('filled', '-')))}</td>"
                      f"<td>{e(str(row.get('action', '-')))}</td><td>{e(str(row.get('note', '')))}</td></tr>")
    rows = (f"<h3>{e(title)}</h3><table><tr><th>Step</th><th>Planner</th><th>Page</th>"
            f"<th>Fields filled (names only)</th><th>Action</th><th>Note</th></tr>{body_rows}</table>")
    figs = "".join(_shot_img(shots, i, f"Step {row.get('step', i + 1)} - page {row.get('page', '?')}")
                   for i, row in enumerate(res["trace"]))
    return rows + f'<div class="gallery">{figs}</div>'


CSS = """body{font-family:Segoe UI,Arial,sans-serif;margin:24px auto;max-width:900px;color:#1c2333}
h1{border-bottom:3px solid #1d3f72;padding-bottom:8px}h3{margin:22px 0 6px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{border:1px solid #c9d2e0;padding:5px 8px;text-align:left}th{background:#eef1f6}
.gallery{display:flex;flex-wrap:wrap;gap:10px}.gallery figure{margin:0;width:280px}
.gallery img{width:100%;border:1px solid #c9d2e0}.gallery figcaption{font-size:11px;color:#556}
.meta{background:#f4f6fb;border:1px solid #c9d2e0;padding:12px 16px;border-radius:6px}
.bad{color:#b00020}.ok{color:#1c7c3b}ul{margin:6px 0}footer{margin-top:26px;font-size:12px;color:#667}"""


def build(ctl) -> str:
    e = html.escape
    outcome = ctl.outcome or ("prepared" if ctl.auto else "in progress")
    receipt = ctl.receipt or {}
    submit_res = getattr(ctl, "last_submit", None)
    missing = ", ".join(ctl.missing) or "none"
    invalid = ", ".join(ctl.errors) or "none"
    corrections = (ctl.auto or {}).get("corrections", []) + (submit_res or {}).get("fill", {}).get("corrections", [])
    corr_rows = "".join(f"<li>field {e(c['field'])} (attempt {c['attempt']})</li>" for c in corrections) \
        or "<li>none</li>"
    timeline = "".join(f"<li>{e(ev)}</li>" for ev in ctl.events) or "<li>no activity</li>"
    receipt_html = (f"<p>Application ID: <b>{e(str(receipt.get('application_id', '-')))}</b><br>"
                    f"Status: <b>{e(str(receipt.get('status', '-')))}</b><br>"
                    f"Submitted at (UTC): {e(str(receipt.get('submitted_at', '-')))}</p>") if receipt else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>CivicPilot audit report</title><style>{CSS}</style></head><body>
<h1>CivicPilot audit report</h1>
<div class="meta">
<b>Service:</b> {e(ctl.service.title)} (local mock portal)<br>
<b>Mode:</b> {e(ctl.mode)}<br>
<b>Outcome:</b> <span class="{'ok' if outcome == 'accepted' else 'bad' if outcome in ('rejected', 'error') else ''}">{e(str(outcome))}</span><br>
<b>Generated (UTC):</b> {datetime.now(timezone.utc).isoformat(timespec='seconds')}<br>
<b>Validation - missing:</b> {e(missing)} · <b>invalid:</b> {e(invalid)}<br>
<b>Format corrections by the agent:</b><ul>{corr_rows}</ul>
{receipt_html}</div>
<h3>Timeline</h3><ul>{timeline}</ul>
{_trace_section('Form preparation (browser agent)', ctl.auto)}
{_trace_section('Final submission (browser agent)', (submit_res or {}).get('fill'))}
<h3>Safety notes</h3>
<ul><li>Values in the trace are field NAMES only; this report contains no profile values.</li>
<li>Screenshots are page images of the mock portal from this session's memory.</li>
<li>Nothing was submitted without the explicit approval checkbox at the Awaiting Approval stage.</li></ul>
<footer>CivicPilot prototype - mock portal, fictional data only. Not connected to any real government system.</footer>
</body></html>"""
