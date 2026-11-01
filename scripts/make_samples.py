"""Generate the fictional sample documents under samples/ (P2-E): small text PDFs, no dependencies.

Run: python3 scripts/make_samples.py
"""
import os
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

MARKSHEET = [
    "RIVERDALE INSTITUTE OF TECHNOLOGY",
    "Official Academic Transcript - FICTIONAL SAMPLE",
    "",
    "Name: Aarav Sharma",
    "Course: B.Tech Computer Science",
    "Year of Study: 3",
    "CGPA: 8.4",
    "",
    "(This document contains fictional data for a hackathon demo only.)",
]
INCOME = [
    "STATE REVENUE DEPARTMENT - INCOME CERTIFICATE",
    "FICTIONAL SAMPLE DOCUMENT",
    "",
    "Name: Aarav Sharma",
    "Annual family income: Rs. 3,50,000",
    "",
    "(Fictional data for the CivicPilot demo only.)",
]
LICENCE = [
    "REGIONAL TRANSPORT OFFICE - DRIVING LICENCE COPY",
    "FICTIONAL SAMPLE DOCUMENT",
    "",
    "Name: Aarav Sharma",
    "DL No: AS0120200012345",
    "DOB: 12/05/2001",
    "Valid Till: 15/12/2026",
    "Class: LMV",
    "PIN: 781001",
    "",
    "(Fictional data for the CivicPilot demo only.)",
]


def _esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def make_pdf(path: Path, lines):
    body = "BT /F1 13 Tf 56 760 Td 20 TL\n"
    for line in lines:
        body += f"({_esc(line)}) Tj T*\n"
    body += "ET"
    stream = body.encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
        b"/Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n").encode()
    path.write_bytes(bytes(out))


def main():
    SAMPLES.mkdir(parents=True, exist_ok=True)
    make_pdf(SAMPLES / "marksheet_sample.pdf", MARKSHEET)
    make_pdf(SAMPLES / "income_certificate_sample.pdf", INCOME)
    make_pdf(SAMPLES / "licence_copy_sample.pdf", LICENCE)
    for p in sorted(SAMPLES.glob("*.pdf")):
        print(f"wrote {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
