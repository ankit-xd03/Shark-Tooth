"""Explicit agent controller: request -> route -> validate -> prepare -> approve -> submit."""
import logging
import re
import uuid
from datetime import datetime, timezone

from core import automation as default_automation
from core import documents, extractor, schema, store

log = logging.getLogger("civicpilot.controller")

STAGES = ["Request Received", "Information Validated", "Form Prepared", "Awaiting Approval", "Submitted"]

QUESTION_BANK = {
    "full_name": ("What is your full name, exactly as on your records?", "e.g. Aarav Sharma"),
    "email": ("What is your email address?", "e.g. aarav.sharma@example.edu"),
    "college": ("Which college or institution are you studying at?", "e.g. Riverdale Institute of Technology"),
    "course": ("Which course or degree are you pursuing?", "e.g. B.Tech Computer Science"),
    "academic_year": ("Which year of study are you in right now?", "e.g. 3 or third"),
    "family_income": ("What is your annual family income?", "e.g. 3.5 lakh or 350000"),
    "annual_income": ("What is your annual household income?", "e.g. 2 lakh or 200000"),
    "cgpa": ("What is your CGPA on a 10-point scale?", "e.g. 8.4"),
    "date_of_birth": ("What is your date of birth?", "e.g. 12/05/2001"),
    "license_number": ("What is your driving licence number?", "e.g. AS0120200012345"),
    "expiry_date": ("When does your licence expire?", "e.g. 15/12/2026"),
    "vehicle_class": ("Which vehicle class is on your licence?", "LMV, MCWG or HMV"),
    "pincode": ("What is the PIN code of your residence?", "e.g. 781001"),
    "consumer_no": ("What is your LPG consumer ID?", "e.g. 5500012345 (10 digits)"),
    "connection_type": ("Is your connection under the Ujjwala (PMUY) scheme or General?", "PMUY or General"),
    "bank_ifsc": ("What is your bank branch's IFSC code?", "e.g. SBIN0001234"),
    "account_last4": ("What are the last 4 digits of your bank account?", "e.g. 4821"),
}


class Controller:
    """`stage` = number of completed STAGES (0-5)."""

    def __init__(self, automation=default_automation):
        self.automation = automation
        self.reset()

    def reset(self):
        self.service = schema.SERVICES["scholarship"]
        self.stage = 0
        self.request = ""
        self.mode = "demo"
        self.fields = {n: "" for n in self.service.names}
        self.sources = {}
        self.clean, self.errors, self.missing = {}, {}, list(self.service.names)
        self.auto = None
        self.outcome = None
        self.receipt = None
        self.tracking = None
        self.eligibility = {}
        self.eligibility_risks = []
        self.otp_pending = False
        self.last_submit = None
        self.message = ""
        self.warning = ""
        self.idem_key = uuid.uuid4().hex
        self.events = []

    def _log(self, msg):
        self.events.append(f"{datetime.now():%H:%M:%S}  {msg}")
        log.info(msg)

    def analyze(self, request: str, profile: dict, service_id: str = None):
        self.message = self.warning = ""
        text = (request or "").strip()
        sid = extractor.classify_service(text) if text else service_id
        if sid not in schema.SERVICES:
            self.message = ("Unsupported service. This prototype supports: "
                            + "; ".join(s.title for s in schema.SERVICES.values()) + ".")
            return
        self.service = schema.SERVICES[sid]
        self._log(f"Request received: {sid}")
        if text:
            extracted, self.mode, warn = extractor.extract(text, sid)
        else:
            extracted, self.mode, warn = {}, "demo", None
        self.warning = warn or ""
        self.request = text or f"(profile only: {sid})"
        merged, self.sources = {}, {}
        for n in self.service.names:
            p = str(profile.get(n, "")).strip()
            if p:
                merged[n], self.sources[n] = p, "profile"
            elif extracted.get(n):
                merged[n], self.sources[n] = extracted[n], "request"
            else:
                merged[n] = ""
        self.fields = merged
        self._revalidate(request_received=True)

    def ingest_document(self, filename: str, data: bytes) -> dict:
        """Extract application fields from an uploaded document. Values keep their source filename."""
        out = documents.ingest(filename, data)
        if self.stage == 0 and out.get("service"):
            self.service = schema.SERVICES[out["service"]]
        merged = [n for n in out["fields"] if n in self.service.names]
        if not merged:
            raise ValueError(f"This document does not contain details for the selected service "
                             f"({self.service.title}).")
        if out.get("service") and out["service"] != self.service.id:
            other = schema.SERVICES[out["service"]]
            out["warning"] = (f"This document looks like a {other.title} document; only the details shared "
                              f"with the selected service were used.")
        for n in merged:
            self.fields[n] = str(out["fields"][n])
            self.sources[n] = out["source"]
        self.request = self.request or f"(document only: {out['source']})"
        self._log(f"Document {filename} provided: {', '.join(merged)}")
        self._revalidate(request_received=True)
        return {**out, "filled": merged}

    def update_fields(self, profile: dict):
        self.message = ""
        self.fields = {n: str(profile.get(n, "")).strip() for n in self.service.names}
        for n, v in self.fields.items():
            self.sources[n] = "profile" if v else self.sources.get(n, "")
        self._revalidate(request_received=self.stage >= 1)

    def _revalidate(self, request_received=True):
        self.clean, self.errors, self.missing = self.service.validate(self.fields)
        self.auto, self.outcome, self.receipt = None, None, None
        self.idem_key = uuid.uuid4().hex
        valid = not self.errors and not self.missing
        self.stage = (2 if valid else 1) if request_received else 0
        self._log("Information validated" if valid else
                  f"Validation: {len(self.missing)} missing, {len(self.errors)} invalid")

    @property
    def is_valid(self):
        return self.stage >= 2 and not self.errors and not self.missing

    def chat_question(self):
        """One targeted question for the first missing or invalid field (None when everything is valid)."""
        if not (self.missing or self.errors):
            return None
        field = self.missing[0] if self.missing else next(iter(self.errors))
        question, example = QUESTION_BANK.get(field, (f"What is your {self.service.labels.get(field, field)}?", ""))
        return {"field": field, "question": question, "example": example,
                "error": self.errors.get(field, "")}

    def chat_reply(self, text: str) -> str:
        """Accept a conversational answer, validate it, and continue. Values are never invented."""
        if self.stage < 1:
            raise RuntimeError("Analyze the request before chatting about details.")
        target = self.missing[0] if self.missing else next(iter(self.errors), None)
        if target is None:
            return "Everything is already filled and valid. You can continue to preparation."
        filled = []
        try:
            raw, _how = extractor.chat_extract(target, text, self.service)
        except ValueError:
            raw = None
        if raw:
            self.fields[target] = raw
            self.sources[target] = "chat"
            filled.append(target)
        for field, value in extractor.demo_extract(text, self.service.id).items():
            if field != target and field in self.service.names and not self.fields.get(field):
                self.fields[field] = value
                self.sources[field] = "chat"
                filled.append(field)
        if not filled:
            label = self.service.labels.get(target, target)
            self._log(f"Chat reply could not fill {target}")
            return (f"I could not read a valid {label} from that reply, so I have not changed anything. "
                    "Please type just the value itself.")
        self._revalidate(request_received=self.stage >= 1)
        names = ", ".join(self.service.labels.get(f, f) for f in filled)
        self._log(f"Chat reply filled: {', '.join(filled)}")
        if self.missing or self.errors:
            nxt = self.chat_question()
            return (f"Noted: {names}. Next: {nxt['question']} {nxt['example']}".strip()
                    if nxt else f"Noted: {names}.")
        return f"Noted: {names}. All required information is now valid — you can authorize the agent."

    def prepare(self):
        if not self.is_valid:
            raise RuntimeError("Cannot prepare the form until all required fields are valid.")
        self.message = ""
        self.eligibility_risks = []
        self._log("Reading the portal's eligibility rules")
        try:
            self.eligibility = self.automation.read_eligibility(self.service.id)
            self.eligibility_risks = self._eligibility_risks(self.eligibility)
        except Exception as e:
            log.warning("eligibility pre-check skipped: %s", type(e).__name__)
            self.eligibility = {}
        if self.eligibility_risks:
            self._log(f"Eligibility pre-check flagged {len(self.eligibility_risks)} risk(s)")
        self._log("Opening mock portal to prepare form")
        self.auto = self.automation.fill_form(self.service.id, self.service.form_values(self.clean), self.idem_key)
        if self.auto["ok"]:
            self.stage = 3
            self._log("Form prepared")
        else:
            self.message = " ".join(self.auto["errors"]) or "Form preparation failed."
            if self.auto["field_errors"]:
                self.errors.update(self.auto["field_errors"])
                self.stage = 1
            self._log("Form preparation failed")

    def _eligibility_risks(self, rules: dict) -> list:
        clean, risks = self.clean, []
        if not rules:
            return risks
        sid = self.service.id
        income = clean.get("family_income") if sid == "scholarship" else clean.get("annual_income")
        if rules.get("income_max") and isinstance(income, (int, float)) and income > rules["income_max"]:
            risks.append(f"Early eligibility warning: annual income (INR {income:,.0f}) exceeds the portal "
                         f"limit of INR {rules['income_max']:,}. Submitting will likely be rejected.")
        if rules.get("min_cgpa") and isinstance(clean.get("cgpa"), (int, float)) \
                and clean["cgpa"] < rules["min_cgpa"]:
            risks.append(f"Early eligibility warning: CGPA {clean['cgpa']:g} is below the portal minimum of "
                         f"{rules['min_cgpa']:g}. Submitting will likely be rejected.")
        if sid == "licence" and rules.get("grace_days") and clean.get("expiry_date") is not None:
            expired = (datetime.now() - clean["expiry_date"]).days
            if expired > rules["grace_days"]:
                risks.append(f"Early eligibility warning: the licence expired {expired} days ago, beyond the "
                             f"{rules['grace_days']}-day renewal window. Submitting will likely be rejected.")
        if sid == "subsidy" and rules.get("connection") and clean.get("connection_type") != rules["connection"]:
            risks.append("Early eligibility warning: the portal restricts this subsidy to PMUY (Ujjwala) "
                         "connections. Submitting will likely be rejected.")
        return risks

    def proceed_to_approval(self):
        if self.stage != 3:
            raise RuntimeError("The form must be prepared before approval.")
        self.stage = 4

    def cancel(self):
        self.auto, self.outcome, self.message = None, None, "Cancelled. Your draft is preserved."
        self.stage = 2 if not (self.errors or self.missing) else 1
        self.idem_key = uuid.uuid4().hex
        self._log("Cancelled by user")

    def submit(self, confirmed: bool):
        if confirmed is not True:
            raise PermissionError("Explicit user approval is required before submission.")
        if self.stage != 4:
            raise RuntimeError("Application is not awaiting approval.")
        if self.outcome == "accepted":
            raise RuntimeError("Already submitted; duplicate submission blocked.")
        if self.outcome == "uncertain":
            raise RuntimeError("Previous result is uncertain; check the portal status first.")
        self.message = ""
        self._log("Submitting with user approval")
        res = self.automation.submit_application(self.service.id, self.service.form_values(self.clean),
                                                 self.idem_key)
        self.last_submit = res
        if res["outcome"] == "otp_required":
            self.otp_pending = True
            self.message = res["message"]
            self._log("Portal requested an OTP; paused and handed control to the user")
            return
        self.otp_pending = False
        self._apply_result(res["outcome"], res["message"], res.get("receipt"))
        if res["outcome"] == "invalid":
            self.errors.update((res.get("fill") or {}).get("field_errors", {}))

    def submit_otp(self, code: str):
        """Continue a paused submission using a code only the user provided. Never guessed, never logged."""
        if not self.otp_pending:
            raise RuntimeError("No OTP challenge is active.")
        code = str(code or "").strip()
        if not re.fullmatch(r"\d{6}", code):
            self.message = "Enter the 6-digit code exactly as it appears in the simulated SMS inbox."
            return
        self._log("Verifying the OTP provided by the user")
        res = self.automation.complete_otp(self.service.id, code, self.idem_key)
        self.last_submit = {**res, "fill": self.last_submit.get("fill") if self.last_submit else None}
        if res["outcome"] == "otp_required":
            self.message = res["message"]
            return
        self.otp_pending = False
        self._apply_result(res["outcome"], res["message"], res.get("receipt"))

    def refresh_tracking(self):
        """Drive the browser to the portal tracking page and read the live status for the receipt ID."""
        app_id = (self.receipt or {}).get("application_id")
        if not app_id:
            self.message = "There is no application ID to track yet."
            return
        self._log(f"Tracking application {app_id}")
        res = self.automation.track_application(app_id)
        if res.get("found"):
            self.tracking = res
            store.update_status(app_id, res["status"])
            self.message = ""
            self._log(f"Tracking status: {res['status']}")
        else:
            self.message = ("The portal tracking page could not confirm this application ID right now. "
                            "Try again in a moment.")

    def check_status(self):
        st = self.automation.portal_status(self.idem_key)
        rec = st.get("record") or {}
        if st.get("found") and rec.get("status") == "ACCEPTED":
            self._apply_result("accepted", "Confirmed via portal status lookup.",
                               {"application_id": rec["application_id"], "status": rec["status"],
                                "submitted_at": rec["submitted_at"], "raw": rec})
        elif st.get("found"):
            self._apply_result("rejected", rec.get("reason", "Rejected by portal."), None)
        elif st.get("reachable"):
            self._apply_result("error", "The portal has no record of this submission, so nothing "
                               "was submitted. It is safe to try again.", None)
        else:
            self.message = "The portal is unreachable, so the status is still unknown."

    def _apply_result(self, outcome, message, receipt):
        self.outcome, self.message, self.receipt = outcome, message, receipt
        if outcome == "accepted":
            self.stage = 5
        self._save_history(outcome, receipt)
        self._log(f"Submission outcome: {outcome}")

    def _save_history(self, outcome, receipt):
        try:
            if outcome == "accepted":
                store.save(self.service.id, receipt["application_id"], "ACCEPTED", receipt["submitted_at"])
            elif outcome == "rejected":
                store.save(self.service.id, "-", "REJECTED", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        except Exception as e:
            log.warning("history not saved: %s", type(e).__name__)
