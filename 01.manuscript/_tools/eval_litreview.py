#!/usr/bin/env python3
"""Eval for a literature review deliverable. Six checks, each able to fail.

Written 2026-09-09 from Seamus's standing rules. A review that passes this is
not necessarily good, but a review that fails it is not issuable.

    python3 01.manuscript/_tools/eval_litreview.py <findings.md> <screening.csv>
"""
import csv
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIB = ROOT / "04.references" / "references.bib"
UA = "deep-learn-alaska-spruce-beetle/1.0 (mailto:seamusrobertmurphy@gmail.com)"
READ_STATES = ("read in full", "abstract only", "title only")

# Minimum extent, set by Seamus on 2026-09-09 so a thin search cannot pass.
# A review that screens forty records has not surveyed a field, it has sampled
# one. The read-in-full floor is deliberately lower than the retained floor,
# because publisher paywalls bound it and honesty about that is the point.
MIN_SCREENED = 80
MIN_RETAINED = 20
MIN_READ_FULL = 6
MIN_PER_SUBTOPIC = 3


def bib_keys():
    return set(re.findall(r"^\s*@\w+\{([^,]+)", BIB.read_text(), re.M))


def check_screening_complete(findings, screening):
    """Every retrieved record is in the table, exclusions with a reason."""
    if not screening.exists():
        return "fail", "no screening table", "one row per record"
    rows = list(csv.DictReader(screening.open()))
    if not rows:
        return "fail", "screening table empty", "one row per record"
    need = {"decision", "reason", "title", "doi"}
    missing = need - set(rows[0])
    if missing:
        return "fail", "columns missing: " + ", ".join(sorted(missing)), \
            "decision, reason, title, doi"
    unreasoned = [r for r in rows
                  if r["decision"] == "excluded" and not r["reason"].strip()]
    inc = sum(1 for r in rows if r["decision"] == "included")
    if unreasoned:
        return "fail", f"{len(unreasoned)} exclusions carry no reason", \
            "every exclusion reasoned"
    return "pass", f"{len(rows)} screened, {inc} included", "one row per record"


def check_read_status_declared(findings, screening):
    """Every source named in the findings declares how far it was read."""
    text = findings.read_text()
    keys = set(re.findall(r"`?@?([A-Z][A-Za-z]+_\d{4}[a-z]?)`?", text))
    if not keys:
        return "fail", "no citation keys found in the findings", "keys present"
    undeclared = []
    for k in keys:
        window = "\n".join(ln for ln in text.split("\n") if k in ln)
        if not any(s in window.lower() for s in READ_STATES):
            undeclared.append(k)
    if undeclared:
        return "fail", f"{len(undeclared)} sources with no read status: " + \
            ", ".join(sorted(undeclared)[:4]), "every source declares one"
    return "pass", f"{len(keys)} sources, all declaring read status", \
        "every source declares one"


def check_quotes_have_pages(findings, screening):
    """Every verbatim quotation carries a page number."""
    text = findings.read_text()
    quotes = [ln for ln in text.split("\n") if ln.strip().startswith(">")]
    if not quotes:
        return "fail", "no verbatim quotations at all", "quotes with pages"
    unpaged = []
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip().startswith(">"):
            near = " ".join(lines[max(0, i - 3):i + 3])
            if not re.search(r"\bp{1,2}\.\s?\d|\bpage\s+\d", near):
                unpaged.append(ln.strip()[:60])
    if unpaged:
        return "fail", f"{len(unpaged)} of {len(quotes)} quotes carry no page", \
            "every quote paged"
    return "pass", f"{len(quotes)} quotations, all paged", "every quote paged"


def check_claims_within_read_status(findings, screening):
    """A title-only source makes no claim about a number."""
    text = findings.read_text()
    bad = []
    for ln in text.split("\n"):
        if "title only" in ln.lower() and re.search(r"\d+\.\d|\d+\s?%|R2|R²", ln):
            bad.append(ln.strip()[:70])
    if bad:
        return "fail", f"{len(bad)} numeric claims from title-only sources", \
            "no claim beyond the read status"
    return "pass", "no numeric claim from a title-only source", \
        "no claim beyond the read status"


def check_keys_in_bibliography(findings, screening):
    """Every key cited in the findings exists in references.bib."""
    text = findings.read_text()
    keys = set(re.findall(r"@([A-Z][A-Za-z]+_\d{4}[a-z]?)", text))
    have = bib_keys()
    absent = sorted(keys - have)
    if absent:
        return "fail", f"{len(absent)} cited but absent from the bibliography: " + \
            ", ".join(absent[:4]), "every key present"
    return "pass", f"{len(keys)} keys, all in the bibliography", \
        "every key present"


def check_no_invented_codes(findings, screening):
    """No numbered finding codes, which appear in no forestry journal."""
    text = findings.read_text()
    codes = re.findall(r"\b(?:R|F|S|L)\d{1,2}\b(?!\s*[=:])", text)
    if codes:
        return "fail", f"{len(codes)} coded findings: " + \
            ", ".join(sorted(set(codes))[:5]), "no coded findings"
    return "pass", "no coded findings", "no coded findings"



def check_extent(findings, screening):
    """The search is wide enough to have surveyed the field."""
    if not screening.exists():
        return "fail", "no screening table", f"{MIN_SCREENED} screened"
    rows = list(csv.DictReader(screening.open()))
    inc = [r for r in rows if r.get("decision") == "included"]
    text = findings.read_text().lower()
    full = text.count("read in full")
    problems = []
    if len(rows) < MIN_SCREENED:
        problems.append(f"{len(rows)} screened, fewer than {MIN_SCREENED}")
    if len(inc) < MIN_RETAINED:
        problems.append(f"{len(inc)} retained, fewer than {MIN_RETAINED}")
    if full < MIN_READ_FULL:
        problems.append(f"{full} read in full, fewer than {MIN_READ_FULL}")
    return ("fail" if problems else "pass",
            "; ".join(problems) or
            f"{len(rows)} screened, {len(inc)} retained, {full} read in full",
            f"{MIN_SCREENED} screened, {MIN_RETAINED} retained, "
            f"{MIN_READ_FULL} read in full")


def check_subtopic_coverage(findings, screening):
    """Every subtopic the brief names carries its own sources.

    A subtopic is a level-two heading in the findings. One with fewer than
    MIN_PER_SUBTOPIC distinct citation keys under it has been listed rather
    than reviewed.
    """
    text = findings.read_text()
    parts = re.split(r"^##\s+(.+)$", text, flags=re.M)
    if len(parts) < 3:
        return "fail", "no subtopic headings found", \
            f"{MIN_PER_SUBTOPIC} sources under each"
    thin = []
    for i in range(1, len(parts), 2):
        head, body = parts[i].strip(), parts[i + 1]
        keys = set(re.findall(r"@([A-Z][A-Za-z]+_\d{4}[a-z]?)", body))
        if len(keys) < MIN_PER_SUBTOPIC:
            thin.append(f"{head} ({len(keys)})")
    if thin:
        return "fail", f"{len(thin)} thin subtopics: " + "; ".join(thin[:4]), \
            f"{MIN_PER_SUBTOPIC} sources under each"
    n = (len(parts) - 1) // 2
    return "pass", f"{n} subtopics, each with {MIN_PER_SUBTOPIC} or more", \
        f"{MIN_PER_SUBTOPIC} sources under each"


CHECKS = [
    ("search wide enough to survey the field", check_extent),
    ("every subtopic carries its own sources", check_subtopic_coverage),
    ("screening table complete", check_screening_complete),
    ("read status declared per source", check_read_status_declared),
    ("every quotation carries a page", check_quotes_have_pages),
    ("claims stay within read status", check_claims_within_read_status),
    ("keys present in the bibliography", check_keys_in_bibliography),
    ("no invented finding codes", check_no_invented_codes),
]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    findings, screening = Path(sys.argv[1]), Path(sys.argv[2])
    if not findings.exists():
        print("findings file not found:", findings)
        return 1
    width = max(len(n) for n, _ in CHECKS)
    fails = 0
    for name, fn in CHECKS:
        try:
            status, measured, expected = fn(findings, screening)
        except Exception as exc:                               # noqa: BLE001
            status, measured = "fail", f"check raised {type(exc).__name__}: {exc}"
        mark = "  ok  " if status == "pass" else " FAIL "
        print(f"{mark} {name:<{width}}  {measured}")
        fails += status != "pass"
    print(f"\n{len(CHECKS)} checks, {fails} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
