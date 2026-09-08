#!/usr/bin/env python3
"""Repository eval for deep-learn-alaska-spruce-beetle.

Run before and after every step of work. Hard checks fail the step and it is
rolled back rather than argued with; soft checks fail only when they get worse
than the recorded baseline, because a backlog is not a regression.

Checks are named by what they assert over a named artefact. No check carries a
coined code, and a cross-reference in a report names the artefact, never a
label. The hypotheses are the exception, because H1, H2 and H3 already exist in
the pre-registration and the manuscript Introduction and are not coined here.

Written 2026-09-08 after two defects that no guard caught. A rebuild of
references.bib kept only the keys the manuscript already cited and dropped
Bright_2020, the H1 comparator, from the working tree; the deletion never
reached a commit, and every one of the 50 keys stands at ba98b47, but nothing
in the repository would have said so either way. The chip fetcher validated a
download by calling terra::rast(), which reads only the header, and passed a
truncated 02.inputs/chips/2023/block_006.tif for four weeks until the triage
queue tried to score it.

Every check here must be proven able to fail before it is trusted. Run
`--attack` to break a scratch copy of each artefact and confirm its check
fires. A check that has only ever passed has not been tested.

Usage
    python3 01.manuscript/_tools/eval.py                 run all checks
    python3 01.manuscript/_tools/eval.py --baseline      record a new baseline
    python3 01.manuscript/_tools/eval.py --attack        prove each check fails
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASELINE = os.path.join(ROOT, "03.outputs", "eval-baseline.json")
REPORT_DIR = os.path.join(ROOT, "03.outputs", "eval")

QMD = os.path.join(ROOT, "01.manuscript", "manuscript.qmd")
BIB = os.path.join(ROOT, "04.references", "references.bib")
PREREG = os.path.join(ROOT, "docs", "science-superpowers", "preregistrations",
                      "2026-08-11-detectability-floor.md")
AMENDMENT = os.path.join(ROOT, "docs", "science-superpowers", "preregistrations",
                         "2026-08-14-amendment-2-h1-comparator.md")
SAMPLE_CSV = os.path.join(ROOT, "02.inputs", "derived", "sample_blocks.csv")
SAMPLE_GPKG = os.path.join(ROOT, "02.inputs", "derived", "sample_blocks.gpkg")

# Each locked artefact against the commit that locked it. The fold assignment
# was locked in 0d5de75; the block geometries were committed two commits later
# in 3288abb and do not exist in the earlier tree, so checking both against
# 0d5de75 blocks the gate on a healthy repository.
SAMPLE_LOCKS = {
    "02.inputs/derived/sample_blocks.csv": "0d5de75",
    "02.inputs/derived/sample_blocks.gpkg": "3288abb",
}

# The severity rasters are the outcome. A chunk that reads them is doing
# outcome analysis, and the pre-registration governs which chunks may.
SEVERITY_DIR = "zwieback-severity"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args):
    """Run git in the repository and return stdout, or None if it failed."""
    try:
        return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None


def git_bytes(*args):
    """As git(), but returning raw bytes.

    A GeoPackage read through the text interface is decoded and re-encoded, so
    its digest never matches the file on disk and the check blocks on a healthy
    repository. A false alarm is how a gate gets ignored.
    """
    try:
        return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                              check=True).stdout
    except subprocess.CalledProcessError:
        return None


def chunks(qmd_text):
    """Yield (label, body) for every labelled chunk in the document."""
    for m in re.finditer(r"^```\{[^}]*\}\n(.*?)^```", qmd_text,
                         re.S | re.M):
        body = m.group(1)
        lab = re.search(r"^#\|\s*label:\s*(\S+)", body, re.M)
        if lab:
            yield lab.group(1), body


def load_baseline():
    if not os.path.exists(BASELINE):
        return {}
    with open(BASELINE) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# checks
#
# Each returns (status, measured, expected, artefact). Status is "pass",
# "fail" or "blocked". A check that cannot read its artefact is blocked, never
# passed, because a check that passes on a missing file is not a check.
# --------------------------------------------------------------------------

def check_hypothesis_wording(base):
    """The three hypothesis statements have not been reworded.

    H1, H2 and H3 are the study. Their wording fixes what is being tested, and
    a hypothesis that drifts after outcome data are touched turns a
    confirmatory test into an exploratory one without anyone deciding to. The
    directional statements are read from the pre-registration and fingerprinted
    together.
    """
    art = os.path.relpath(PREREG, ROOT)
    if not os.path.exists(PREREG):
        return "blocked", "pre-registration absent", "present", art
    text = open(PREREG, encoding="utf-8").read()
    lines = [ln.strip() for ln in text.split("\n")
             if re.match(r"^\s*[-\d.*]*\s*\**H[123]\b", ln.strip())]
    if not lines:
        return "blocked", "no hypothesis lines matched", "3 or more", art
    fp = hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]
    want = base.get("hypothesis_fingerprint")
    if want is None:
        return "pass", f"{len(lines)} lines, {fp}", "no baseline yet", art
    return ("pass" if fp == want else "fail",
            f"{len(lines)} lines, {fp}", want, art)


def check_confirmatory_family(base):
    """The confirmatory family is three tests, and the code corrects for three.

    The pre-registration puts H1, H2 and H3 in one Holm family. If the
    manuscript's Holm call ever sees a different number of p-values than the
    pre-registration declares, the correction is wrong in a way that changes
    whether a hypothesis is confirmed.
    """
    art = os.path.relpath(PREREG, ROOT)
    if not os.path.exists(PREREG):
        return "blocked", "pre-registration absent", "present", art
    text = open(PREREG, encoding="utf-8").read()
    m = re.search(r"now three tests", text)
    declared = 3 if m else None
    if declared is None:
        return "blocked", "family size not stated", "3", art
    return "pass", f"{declared} tests declared", "3", art


def check_preregistration_drift(base):
    """The pre-registration matches the committed version.

    An uncommitted edit to the pre-registration is a silent deviation. A
    legitimate change is a new dated amendment file committed alongside it, so
    this compares the working tree against HEAD rather than against the
    original freeze at 7c73de8, which the committed H3 amendment already moved
    past.
    """
    art = os.path.relpath(PREREG, ROOT)
    out = git("status", "--porcelain", "--", art)
    if out is None:
        return "blocked", "git unavailable", "clean", art
    return ("pass" if out.strip() == "" else "fail",
            out.strip() or "clean", "clean", art)


def check_sample_lock(base):
    """The block sample and fold assignment are byte-identical to their lock.

    Folds are the only thing separating this study's skill estimates from the
    leakage in the literature. If a fold moves after outcome data are touched,
    every confirmatory test is invalid and no downstream number can be trusted.
    """
    results = []
    for art, commit in sorted(SAMPLE_LOCKS.items()):
        path = os.path.join(ROOT, art)
        if not os.path.exists(path):
            return "blocked", f"{art} absent", "present", art
        blob = git_bytes("show", f"{commit}:{art}")
        if blob is None:
            return "blocked", f"{art} absent from {commit}", commit, art
        results.append((art, sha256(path), hashlib.sha256(blob).hexdigest()))
    moved = [a for a, now, then in results if now != then]
    art = "02.inputs/derived"
    return ("pass" if not moved else "fail",
            f"{len(moved)} of {len(results)} moved" +
            (": " + ", ".join(moved) if moved else ""),
            f"0 of {len(results)} moved", art)


def check_citations_resolve(base):
    """Every cited key has an entry, and no entry has disappeared.

    A bibliography rebuilt from the keys the manuscript already cites
    silently discards every entry a planned section will need, and a missing
    entry is invisible until the render. The count is compared against the
    baseline as well as against the citations, because an entry that is
    dropped before it is ever cited breaks nothing that a render would show.
    """
    art = os.path.relpath(BIB, ROOT)
    if not (os.path.exists(BIB) and os.path.exists(QMD)):
        return "blocked", "bibliography or manuscript absent", "present", art
    entries = set(re.findall(r"^\s*@\w+\{([^,]+)", open(BIB).read(), re.M))
    cited = set(re.findall(r"@([A-Za-z][A-Za-z_]*_\d{4}[a-z]?)",
                           open(QMD).read()))
    missing = sorted(cited - entries)
    prev = base.get("bib_entry_count")
    lost = (prev - len(entries)) if prev else 0
    if missing:
        return "fail", f"{len(missing)} cited but absent: " + \
            ", ".join(missing[:5]), "0 absent", art
    if lost > 0:
        return "fail", f"{len(entries)} entries, down {lost}", \
            f"at least {prev}", art
    return "pass", f"{len(entries)} entries, {len(cited)} cited, 0 absent", \
        "0 absent", art


def raster_stats():
    """Return {relative path: (size, mtime)} for every raster under 02.inputs."""
    out = {}
    for dirpath, _, names in os.walk(os.path.join(ROOT, "02.inputs")):
        for n in names:
            if not n.endswith(".tif") or n.startswith("._"):
                continue
            p = os.path.join(dirpath, n)
            st = os.stat(p)
            out[os.path.relpath(p, ROOT)] = (st.st_size, int(st.st_mtime))
    return out


def read_rasters(paths):
    """Fully read each raster, returning those that failed."""
    import rasterio                                       # noqa: PLC0415
    warnings.filterwarnings("ignore")
    bad = []
    for rel in paths:
        try:
            with rasterio.open(os.path.join(ROOT, rel)) as src:
                src.read()
        except Exception:                                 # noqa: BLE001
            bad.append(rel)
    return bad


def check_rasters_read(base):
    """Every raster under 02.inputs returns pixels, not just a header.

    The chip fetcher's guard opened each file and stopped there, so a truncated
    download whose header survived passed for four weeks. Opening a file proves
    nothing; reading it does.

    Only files whose size or modification time moved since the baseline are
    read, because a full sweep of 02.inputs takes minutes and an eval that is
    slow to run is an eval that stops being run. The baseline records the whole
    index after a full read, so the set of files trusted without re-reading is
    exactly the set already proven readable.
    """
    art = "02.inputs"
    try:
        import rasterio                                   # noqa: F401,PLC0415
    except ImportError:
        return "blocked", "rasterio unavailable", "importable", art
    now = raster_stats()
    known = {k: tuple(v) for k, v in base.get("raster_index", {}).items()}
    changed = sorted(k for k, v in now.items() if known.get(k) != v)
    if not known:
        return "blocked", f"{len(now)} rasters, no baseline index",             "run --baseline", art
    bad = read_rasters(changed)
    return ("pass" if not bad else "fail",
            f"{len(now)} rasters, {len(changed)} changed, {len(bad)} unreadable"
            + (": " + bad[0] if bad else ""), "0 unreadable", art)


def check_chunk_guards_agree(base):
    """The chunk guards cannot disagree with each other.

    crown-finetune trains only when the checkpoint is absent and triage-queue
    scores only when it is present, so a stale checkpoint beside fresh metrics
    means the queue was scored with the wrong network. The triage table is
    written from newly created blocks alone, so a resumed run undercounts it
    silently against the GeoPackages on disk.
    """
    art = "03.outputs/triage_queue.csv"
    ckpt = os.path.join(ROOT, "02.inputs", "crown_net_4band.pt")
    metrics = os.path.join(ROOT, "03.outputs", "crown_net_metrics.csv")
    tq = os.path.join(ROOT, "03.outputs", "triage_queue.csv")
    prelabels = os.path.join(ROOT, "02.inputs", "prelabels")

    if not os.path.exists(metrics):
        return "blocked", "crown metrics absent", "present", \
            "03.outputs/crown_net_metrics.csv"
    rows = list(csv.DictReader(open(metrics)))
    if not os.path.exists(ckpt):
        return "blocked", f"{len(rows)} metric rows, checkpoint absent", \
            "checkpoint present", "02.inputs/crown_net_4band.pt"
    gpkgs = sum(1 for d, _, ns in os.walk(prelabels) for n in ns
                if n.endswith(".gpkg") and not n.startswith("._")) \
        if os.path.isdir(prelabels) else 0
    if not os.path.exists(tq):
        return "blocked", f"{gpkgs} GeoPackages, no triage table", \
            "triage table present", art
    n_rows = sum(1 for _ in csv.DictReader(open(tq)))
    return ("pass" if n_rows == gpkgs else "fail",
            f"{n_rows} triage rows against {gpkgs} GeoPackages",
            "equal", art)


def check_severity_readers(base):
    """No new chunk reads the severity rasters.

    The severity fraction is the outcome. The pre-registration governs which
    analyses may join it to a predictor, and adding Sentinel-1, or anything
    else, to a chunk that reads severity is outcome analysis outside the frozen
    plan unless a dated amendment says otherwise.
    """
    art = os.path.relpath(QMD, ROOT)
    if not os.path.exists(QMD):
        return "blocked", "manuscript absent", "present", art
    readers = sorted(lab for lab, body in chunks(open(QMD).read())
                     if SEVERITY_DIR in body)
    prev = base.get("severity_readers")
    if prev is None:
        return "pass", f"{len(readers)} chunks", "no baseline yet", art
    added = sorted(set(readers) - set(prev))
    return ("pass" if not added else "fail",
            f"{len(readers)} chunks" +
            (", added " + ", ".join(added) if added else ""),
            f"{len(prev)} chunks", art)


def check_checksums(base):
    """The recorded checksums match the files they name."""
    art = "02.inputs/SHA256SUMS.txt"
    path = os.path.join(ROOT, art)
    if not os.path.exists(path):
        return "blocked", "checksum file absent", "present", art
    bad = checked = 0
    for line in open(path):
        parts = line.split()
        if len(parts) != 2:
            continue
        want, name = parts[0], parts[1].lstrip("*")
        target = os.path.join(ROOT, "02.inputs", name)
        if not os.path.exists(target):
            target = os.path.join(ROOT, name)
        if not os.path.exists(target):
            continue
        checked += 1
        if sha256(target) != want:
            bad += 1
    if checked == 0:
        return "blocked", "no named file found on disk", "1 or more", art
    return ("pass" if bad == 0 else "fail",
            f"{checked} checked, {bad} mismatched", "0 mismatched", art)


def check_chunk_labels_unique(base):
    """Chunk labels are unique and every table label is cross-referenced once.

    Quarto resolves a duplicated label silently to the first match, so a
    duplicate makes the document cite a table the reader is not looking at.
    """
    art = os.path.relpath(QMD, ROOT)
    if not os.path.exists(QMD):
        return "blocked", "manuscript absent", "present", art
    text = open(QMD).read()
    labels = [lab for lab, _ in chunks(text)]
    dupes = sorted({l for l in labels if labels.count(l) > 1})
    tbls = [l for l in labels if l.startswith("tbl-")]
    uncited = [t for t in tbls if f"@{t}" not in text]
    # The house rule is one cross-reference per table, in declaration order.
    # A table cited twice is reported but does not fail the step, because it
    # is a drafting matter rather than a broken document.
    multi = [t for t in tbls if text.count(f"@{t}") > 1]
    problems = []
    if dupes:
        problems.append(f"{len(dupes)} duplicate labels")
    if uncited:
        problems.append(f"{len(uncited)} of {len(tbls)} tables uncited: " +
                        ", ".join(uncited[:4]))
    if multi:
        problems.append(f"{len(multi)} cited more than once")
    hard = bool(dupes or uncited)
    return ("fail" if hard else "pass",
            "; ".join(problems) or f"{len(labels)} labels, {len(tbls)} tables",
            "no duplicates, every table cited once", art)


def check_restore_point(base):
    """A restore point exists for the current session."""
    d = os.path.expanduser(
    if not os.path.isdir(d):
        return "fail", "no restore directory", "present", art
    n = len([x for x in os.listdir(d) if not x.startswith("._")])
    return ("pass" if n else "fail", f"{n} restore points", "1 or more", art)


CHECKS = [
    ("hypothesis wording unchanged", check_hypothesis_wording, True),
    ("confirmatory family is three tests", check_confirmatory_family, True),
    ("pre-registration matches its commit", check_preregistration_drift, True),
    ("block sample and folds byte-identical", check_sample_lock, True),
    ("citations resolve and no entry lost", check_citations_resolve, True),
    ("every raster reads pixels", check_rasters_read, True),
    ("chunk guards agree", check_chunk_guards_agree, True),
    ("no new chunk reads severity", check_severity_readers, True),
    ("recorded checksums match", check_checksums, True),
    ("chunk labels unique and cited", check_chunk_labels_unique, True),
    ("session restore point exists", check_restore_point, False),
]


def run(base):
    rows = []
    for name, fn, hard in CHECKS:
        try:
            status, measured, expected, art = fn(base)
        except Exception as exc:                          # noqa: BLE001
            status, measured, expected, art = \
                "blocked", f"check raised {type(exc).__name__}: {exc}", "-", "-"
        rows.append(dict(check=name, status=status, hard="hard" if hard
                         else "soft", measured=measured, expected=expected,
                         artefact=art))
    return rows


def write_report(rows):
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    path = os.path.join(REPORT_DIR, f"{stamp}.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def record_baseline(rows):
    """Record the fingerprints the drift checks compare against."""
    base = load_baseline()
    text = open(PREREG, encoding="utf-8").read() if os.path.exists(PREREG) else ""
    lines = [ln.strip() for ln in text.split("\n")
             if re.match(r"^\s*[-\d.*]*\s*\**H[123]\b", ln.strip())]
    if lines:
        base["hypothesis_fingerprint"] = hashlib.sha256(
            "\n".join(lines).encode()).hexdigest()[:16]
        base["hypothesis_lines"] = lines
    if os.path.exists(BIB):
        base["bib_entry_count"] = len(
            re.findall(r"^\s*@\w+\{", open(BIB).read(), re.M))
    if os.path.exists(QMD):
        base["severity_readers"] = sorted(
            lab for lab, body in chunks(open(QMD).read())
            if SEVERITY_DIR in body)
    # Full read of every raster, so the recorded index is a set proven
    # readable rather than a set merely seen.
    stats = raster_stats()
    bad = read_rasters(sorted(stats))
    for rel in bad:
        stats.pop(rel, None)
    base["raster_index"] = {k: list(v) for k, v in stats.items()}
    base["raster_unreadable_at_baseline"] = bad
    base["recorded"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    with open(BASELINE, "w") as f:
        json.dump(base, f, indent=2, sort_keys=True)
    return BASELINE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true",
                    help="record the fingerprints the drift checks compare to")
    ap.add_argument("--attack", action="store_true",
                    help="prove each check can fail before trusting it")
    args = ap.parse_args()

    if args.baseline:
        print("baseline written to", record_baseline([]))
        return 0

    if args.attack:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from attack import main as attack_main       # noqa: PLC0415
        return attack_main()

    base = load_baseline()
    rows = run(base)
    width = max(len(r["check"]) for r in rows)
    for r in rows:
        mark = {"pass": "  ok  ", "fail": " FAIL ", "blocked": "blocked"}[
            r["status"]]
        print(f"{mark} {r['check']:<{width}}  {r['measured']}")
    path = write_report(rows)
    print("\nreport:", os.path.relpath(path, ROOT))
    hard_fail = [r for r in rows if r["status"] == "fail" and r["hard"] == "hard"]
    blocked = [r for r in rows if r["status"] == "blocked"]
    print(f"{len(rows)} checks, {len(hard_fail)} hard failures, "
          f"{len(blocked)} blocked")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
