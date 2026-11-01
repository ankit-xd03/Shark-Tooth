"""Randomized portal robustness benchmark (P1-C).

Runs the rule-based browser agent against N seeded random portal layouts per service, in demo mode,
and prints an honest success-rate table with failure reasons.

Usage:
    python3 scripts/benchmark.py                       # 20 seeds per service, demo mode
    python3 scripts/benchmark.py --seeds 40 --submit   # more seeds; also submit after preparing
    python3 scripts/benchmark.py --llm                 # use the configured LLM key, if any

Seeds 1..10 are the tuning range; 11..N are treated as held-out (never tuned on).
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
from core import automation, schema  # noqa: E402
from portal import server  # noqa: E402

PROFILES = {
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
TUNE_SEEDS = range(1, 11)


def values_for(sid):
    svc = schema.get(sid)
    return svc.form_values(svc.validate(PROFILES[sid])[0])


def run_seed(sid, seed, base, submit=False):
    key = f"bench-{seed}-{sid}"
    res = automation.fill_form(sid, values_for(sid), key, base)
    entry = {"service": sid, "seed": seed, "ok": bool(res["ok"]),
             "reason": "" if res["ok"] else " | ".join(res["errors"]) or "unknown",
             "corrections": len(res.get("corrections", []))}
    if res["ok"] and submit:
        out = automation.submit_application(sid, values_for(sid), key, base)
        entry["ok"] = out["outcome"] == "accepted"
        if not entry["ok"]:
            entry["reason"] = f"submit {out['outcome']}: {out['message'][:120]}"
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=20, help="seeds per service (1..N)")
    ap.add_argument("--services", default="scholarship,licence,subsidy")
    ap.add_argument("--submit", action="store_true", help="also submit after preparing")
    ap.add_argument("--llm", action="store_true", help="do not force demo mode (uses configured key)")
    args = ap.parse_args()
    if not args.llm:
        os.environ["DEMO_MODE"] = "true"
    if not server.is_up():
        server.start_in_thread()
    base = config.PORTAL_URL
    rows, t0 = [], time.time()
    for sid in [s.strip() for s in args.services.split(",") if s.strip() in PROFILES]:
        for seed in range(1, args.seeds + 1):
            rows.append(run_seed(sid, seed, base, args.submit))
    print(f"\nCivicPilot randomized-portal benchmark  (mode: {'llm' if args.llm else 'demo'}, "
          f"submit: {args.submit}, {time.time() - t0:.0f}s)\n")
    print(f"{'service':<12} {'seed':>4}  {'result':<8} {'fixes':>5}  reason")
    print("-" * 88)
    for r in rows:
        print(f"{r['service']:<12} {r['seed']:>4}  {'PASS' if r['ok'] else 'FAIL':<8} "
              f"{r['corrections']:>5}  {r['reason'][:70]}")
    print("-" * 88)
    for sid in sorted({r["service"] for r in rows}):
        sub = [r for r in rows if r["service"] == sid]
        tune = [r for r in sub if r["seed"] in TUNE_SEEDS]
        held = [r for r in sub if r["seed"] not in TUNE_SEEDS]
        pct = lambda g: f"{100 * sum(r['ok'] for r in g) / len(g):5.1f}%" if g else "  n/a"
        print(f"{sid:<12} overall {pct(sub)}  tuning(1-10) {pct(tune)}  held-out(11+) {pct(held)}")
    print("\nNote: seeds 1-10 were used to tune planner hints; treat held-out numbers as the honest score.")
    print("Layouts include: label synonyms, shuffled field order, decoy fields/buttons, randomized ids,")
    print("extra instruction interstitials, dropdown wording variants and DD-MM-YYYY date portals.")


if __name__ == "__main__":
    main()
