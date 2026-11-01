import re
from dataclasses import dataclass
from datetime import date, datetime

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def parse_income(raw: str) -> float:
    s = str(raw).translate(DEV_DIGITS).lower().replace(",", "").replace("₹", "")
    for junk in ("inr", "rs.", "rs"):
        s = s.replace(junk, "")
    mult = 1
    if "lakh" in s or "lpa" in s or "लाख" in s:
        mult = 100_000
        s = re.sub(r"lakhs?|lpa|लाख", "", s)
    s = s.strip()
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        raise ValueError("Enter income as a number, e.g. 350000, 3.5 lakh or ३.५ लाख")
    return float(s) * mult


def parse_date(raw: str) -> date:
    s = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("Enter the date as DD/MM/YYYY, e.g. 15/12/2026")


def _name(raw):
    if not re.fullmatch(r"[A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F .'-]{1,79}", raw):
        raise ValueError("Name must contain letters only (2-80 characters)")
    return raw


def _email(raw):
    if not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", raw):
        raise ValueError("Enter a valid email address")
    return raw


def _text(raw):
    if not 2 <= len(raw) <= 120:
        raise ValueError("Must be 2-120 characters")
    return raw


def _year(raw):
    raw = str(raw).translate(DEV_DIGITS).strip()
    if not re.fullmatch(r"\d", raw) or not 1 <= int(raw) <= 6:
        raise ValueError("Academic year must be a whole number from 1 to 6")
    return int(raw)


def _income(raw):
    v = parse_income(raw)
    if v > 1e9:
        raise ValueError("Income value is unrealistically large")
    return v


def _cgpa(raw):
    try:
        v = float(str(raw).translate(DEV_DIGITS))
    except ValueError:
        raise ValueError("CGPA must be a number between 0 and 10")
    if not 0 <= v <= 10:
        raise ValueError("CGPA must be between 0 and 10")
    return v


def _licence_no(raw):
    s = re.sub(r"[\s-]", "", raw).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{13}", s):
        raise ValueError("Licence number must be 2 letters followed by 13 digits, e.g. AS0120200012345")
    return s


def _dob(raw):
    d = parse_date(raw)
    today = date.today()
    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    if age < 18:
        raise ValueError("Applicant must be at least 18 years old")
    if age > 100:
        raise ValueError("Date of birth looks unrealistic")
    return d


def _expiry(raw):
    d = parse_date(raw)
    if not 1990 <= d.year <= date.today().year + 20:
        raise ValueError("Expiry date looks unrealistic")
    return d


CLASS_ALIASES = {
    "LMV": ("lmv", "car", "light motor vehicle"),
    "MCWG": ("mcwg", "bike", "motorcycle", "motorbike", "two wheeler", "motorcycle with gear"),
    "HMV": ("hmv", "truck", "heavy motor vehicle"),
}


def _vehicle(raw):
    s = " ".join(re.findall(r"[a-z]+", raw.lower()))
    for code, aliases in CLASS_ALIASES.items():
        if s in aliases:
            return code
    raise ValueError("Vehicle class must be one of LMV, MCWG, HMV")


def _pin(raw):
    if not re.fullmatch(r"[1-9]\d{5}", raw):
        raise ValueError("PIN code must be 6 digits")
    return raw


def _consumer_no(raw):
    s = re.sub(r"[\s-]", "", raw)
    if not re.fullmatch(r"\d{10}", s):
        raise ValueError("LPG consumer ID must be 10 digits")
    return s


CONN_TYPE_ALIASES = {
    "PMUY": ("pmuy", "pm ujjwala", "ujjwala"),
    "GENERAL": ("general", "regular", "non-ujjwala", "non ujjwala", "ordinary"),
}


def _connection_type(raw):
    s = " ".join(re.findall(r"[a-z]+", raw.lower()))
    for code, aliases in CONN_TYPE_ALIASES.items():
        if s in aliases:
            return code
    raise ValueError("Connection type must be PMUY (Ujjwala) or General")


def _ifsc(raw):
    s = re.sub(r"[\s]", "", raw).upper()
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", s):
        raise ValueError("IFSC code must be 4 letters, a zero, then 6 characters, e.g. SBIN0001234")
    return s


def _account_last4(raw):
    s = re.sub(r"[\s]", "", raw)
    if not re.fullmatch(r"\d{4}", s):
        raise ValueError("Enter exactly the last 4 digits of the bank account")
    return s


def _fmt_date(d):
    return d.strftime("%d/%m/%Y")


@dataclass(frozen=True, eq=False)
class Service:
    id: str
    title: str
    short: str
    pattern: re.Pattern
    fields: tuple
    validators: dict
    formatters: dict

    @property
    def names(self):
        return [n for n, _ in self.fields]

    @property
    def labels(self):
        return dict(self.fields)

    def validate(self, fields: dict):
        clean, errors, missing = {}, {}, []
        for name in self.names:
            raw = str(fields.get(name) or "").strip()
            if not raw:
                missing.append(name)
                continue
            try:
                clean[name] = self.validators[name](raw)
            except ValueError as e:
                errors[name] = str(e)
        return clean, errors, missing

    def form_values(self, clean: dict) -> dict:
        return {k: self.formatters.get(k, str)(v) for k, v in clean.items()}


SERVICES = {
    "scholarship": Service(
        id="scholarship",
        title="Student scholarship application",
        short="student scholarship",
        pattern=re.compile(r"scholarship|financial aid|educational assistance|stipend|bursary|छात्रवृत्ति", re.I),
        fields=(("full_name", "Full name"), ("email", "Email"), ("college", "College / institution"),
                ("course", "Course / degree"), ("academic_year", "Academic year (1-6)"),
                ("family_income", "Annual family income (INR)"), ("cgpa", "CGPA (0-10)")),
        validators={"full_name": _name, "email": _email, "college": _text, "course": _text,
                    "academic_year": _year, "family_income": _income, "cgpa": _cgpa},
        formatters={"academic_year": lambda v: str(int(v)), "family_income": lambda v: str(int(v)),
                    "cgpa": lambda v: f"{v:g}"},
    ),
    "licence": Service(
        id="licence",
        title="Driving licence renewal",
        short="driving licence renewal",
        pattern=re.compile(r"licen[cs]e|driving|\bdl\b|\brto\b|लाइसेंस|लाइसेन्स|ड्राइविंग", re.I),
        fields=(("full_name", "Full name (as on licence)"), ("email", "Email"),
                ("date_of_birth", "Date of birth (DD/MM/YYYY)"), ("license_number", "Driving licence number"),
                ("expiry_date", "Licence expiry date (DD/MM/YYYY)"),
                ("vehicle_class", "Vehicle class (LMV / MCWG / HMV)"), ("pincode", "PIN code of residence")),
        validators={"full_name": _name, "email": _email, "date_of_birth": _dob, "license_number": _licence_no,
                    "expiry_date": _expiry, "vehicle_class": _vehicle, "pincode": _pin},
        formatters={"date_of_birth": _fmt_date, "expiry_date": _fmt_date},
    ),
    "subsidy": Service(
        id="subsidy",
        title="LPG connection subsidy claim",
        short="LPG connection subsidy claim",
        pattern=re.compile(r"subsidy|\blpg\b|ujjwala|सब्सिडी|एलपीजी", re.I),
        fields=(("full_name", "Full name"), ("email", "Email"),
                ("consumer_no", "LPG consumer ID (10 digits)"),
                ("connection_type", "Connection type (PMUY / General)"),
                ("bank_ifsc", "Bank IFSC code"), ("account_last4", "Bank account (last 4 digits)"),
                ("annual_income", "Annual household income (INR)")),
        validators={"full_name": _name, "email": _email, "consumer_no": _consumer_no,
                    "connection_type": _connection_type, "bank_ifsc": _ifsc,
                    "account_last4": _account_last4, "annual_income": _income},
        formatters={"annual_income": lambda v: str(int(v))},
    ),
}

ALL_FIELD_NAMES = list(dict.fromkeys(n for s in SERVICES.values() for n in s.names))

_KIND_BY_VALIDATOR = {"_dob": "date", "_expiry": "date", "_income": "income", "_pin": "pin"}


def get_field_kind(field: str):
    """Coarse type of a field, used for safe re-formatting on portal format errors."""
    for s in SERVICES.values():
        v = s.validators.get(field)
        if v is not None:
            return _KIND_BY_VALIDATOR.get(v.__name__)
    return None


def get(service_id: str) -> Service:
    return SERVICES[service_id]


def detect_service(text: str):
    for s in SERVICES.values():
        if s.pattern.search(text or ""):
            return s.id
    return None
