#!/usr/bin/env python3
"""Prove each eval check can fail.

A check that has only ever passed has not been tested. This breaks each
artefact in the way the check is supposed to notice, confirms the check
reports a failure, then restores the artefact and verifies the restoration by
hash. Anything that cannot be broken reversibly is attacked on a copy instead.

Run through the eval, not directly:
    python3 01.manuscript/_tools/eval.py --attack
"""

import hashlib
import os
import re
import shutil
import sys
import tempfile

import eval as ev


class Perturb:
    """Edit a file, run a check, restore it, and verify the restoration."""

    def __init__(self, path):
        self.path = path
        self.before = None

    def __enter__(self):
        with open(self.path, "rb") as f:
            self.before = f.read()
        self.digest = hashlib.sha256(self.before).hexdigest()
        return self

    def write(self, data):
        with open(self.path, "wb") as f:
            f.write(data)

    def __exit__(self, *exc):
        with open(self.path, "wb") as f:
            f.write(self.before)
        after = hashlib.sha256(open(self.path, "rb").read()).hexdigest()
        if after != self.digest:
            raise RuntimeError("restore failed for " + self.path)
        return False


def attack_hypothesis_wording(base):
    """Reword a hypothesis and confirm the fingerprint moves."""
    with Perturb(ev.PREREG) as p:
        text = p.before.decode()
        broken = text.replace("higher recall at 0.90 precision",
                              "higher recall at 0.80 precision", 1)
        if broken == text:
            return None, "could not find the H1 wording to alter"
        p.write(broken.encode())
        return ev.check_hypothesis_wording(base)[0], "H1 threshold reworded"


def attack_confirmatory_family(base):
    """Remove the declared family size and confirm the check blocks."""
    with Perturb(ev.PREREG) as p:
        p.write(p.before.decode().replace("now three tests",
                                          "now several tests").encode())
        return ev.check_confirmatory_family(base)[0], "family size unstated"


def attack_preregistration_drift(base):
    """Append a line and confirm the working tree is seen as dirty."""
    with Perturb(ev.PREREG) as p:
        p.write(p.before + b"\nAn undeclared deviation.\n")
        return ev.check_preregistration_drift(base)[0], "one line appended"


def attack_sample_lock(base):
    """Move a fold assignment and confirm the lock check notices."""
    with Perturb(ev.SAMPLE_CSV) as p:
        lines = p.before.decode().split("\n")
        if len(lines) < 3:
            return None, "sample table too short to perturb"
        lines[2] = lines[2] + " "
        p.write("\n".join(lines).encode())
        return ev.check_sample_lock(base)[0], "one byte added to a block row"


def drop_entry(text, key):
    """Return text with the bibliography entry for key removed, braces counted."""
    m = re.search(r"@\w+\{%s\s*," % re.escape(key), text)
    if not m:
        return text
    i = text.index("{", m.start())
    depth, j = 0, i
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return text[:m.start()] + text[j + 1:]


def attack_citations_resolve(base):
    """Delete the H1 comparator's entry, the defect this check exists for.

    The entry is matched by counting braces rather than by a pattern ending in
    a newline, because references.bib has been written both one entry per line
    and one field per line, and a pattern that fits one format silently matches
    nothing in the other, which leaves the check untested rather than failing.
    """
    with Perturb(ev.BIB) as p:
        text = p.before.decode()
        broken = drop_entry(text, "Bright_2020")
        if broken == text:
            return None, "Bright_2020 entry not found to delete"
        p.write(broken.encode())
        return ev.check_citations_resolve(base)[0], "Bright_2020 entry deleted"


def attack_rasters_read(base):
    """Truncate a copy of a real raster and confirm the read fails.

    Attacked on a copy rather than in place, because a truncation that is not
    perfectly reversed would destroy an input.
    """
    src = None
    for rel in sorted(base.get("raster_index", {})):
        if rel.endswith(".tif"):
            src = rel
            break
    if src is None:
        return None, "no raster in the baseline index"
    with tempfile.TemporaryDirectory() as d:
        dst = os.path.join(d, os.path.basename(src))
        shutil.copy2(os.path.join(ev.ROOT, src), dst)
        size = os.path.getsize(dst)
        with open(dst, "r+b") as f:
            f.truncate(int(size * 0.6))
        # Call the reader directly, since the check walks the real tree.
        import rasterio                                   # noqa: PLC0415
        import warnings                                   # noqa: PLC0415
        warnings.filterwarnings("ignore")
        try:
            with rasterio.open(dst) as s:
                s.read()
            return "pass", f"truncated {src} still read, guard is blind"
        except Exception:                                 # noqa: BLE001
            return "fail", f"truncated {src} to 60 per cent"


def attack_chunk_guards_agree(base):
    """Hide a GeoPackage and confirm the count mismatch is seen."""
    prelabels = os.path.join(ev.ROOT, "02.inputs", "prelabels")
    found = None
    for dirpath, _, names in os.walk(prelabels):
        for n in names:
            if n.endswith(".gpkg") and not n.startswith("._"):
                found = os.path.join(dirpath, n)
                break
        if found:
            break
    if found is None:
        return None, "no GeoPackage on disk to hide"
    moved = found + ".attack"
    os.rename(found, moved)
    try:
        return ev.check_chunk_guards_agree(base)[0], "one GeoPackage hidden"
    finally:
        os.rename(moved, found)


def attack_severity_readers(base):
    """Claim a chunk newly reads severity and confirm the check notices."""
    shrunk = dict(base)
    readers = base.get("severity_readers") or []
    if not readers:
        return None, "no severity readers recorded in the baseline"
    shrunk["severity_readers"] = readers[1:]
    return ev.check_severity_readers(shrunk)[0], \
        f"baseline shrunk by one, {readers[0]} looks new"


def attack_checksums(base):
    """Corrupt a recorded digest and confirm the mismatch is seen."""
    path = os.path.join(ev.ROOT, "02.inputs", "SHA256SUMS.txt")
    if not os.path.exists(path):
        return None, "no checksum file present"
    with Perturb(path) as p:
        lines = p.before.decode().split("\n")
        for i, ln in enumerate(lines):
            parts = ln.split()
            if len(parts) == 2 and len(parts[0]) == 64:
                lines[i] = ("0" * 64) + " " + parts[1]
                break
        else:
            return None, "no digest line found to corrupt"
        p.write("\n".join(lines).encode())
        return ev.check_checksums(base)[0], "one digest zeroed"


def attack_chunk_labels_unique(base):
    """Duplicate a chunk label and confirm the clash is seen."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^#\|\s*label:\s*(tbl-\S+)", text, re.M)
        if not m:
            return None, "no table label found to duplicate"
        first = re.search(r"^#\|\s*label:\s*\S+", text, re.M)
        broken = text[:first.start()] + f"#| label: {m.group(1)}" + \
            text[first.end():]
        p.write(broken.encode())
        return ev.check_chunk_labels_unique(base)[0], \
            f"{m.group(1)} duplicated onto the first chunk"


def attack_restore_point(base):
    """Point the check at a directory that does not exist."""
    real = os.path.expanduser
    os.path.expanduser = lambda p: p + "-does-not-exist"
    try:
        return ev.check_restore_point(base)[0], "restore path redirected"
    finally:
        os.path.expanduser = real


ATTACKS = [
    ("hypothesis wording unchanged", attack_hypothesis_wording),
    ("confirmatory family is three tests", attack_confirmatory_family),
    ("pre-registration matches its commit", attack_preregistration_drift),
    ("block sample and folds byte-identical", attack_sample_lock),
    ("citations resolve and no entry lost", attack_citations_resolve),
    ("every raster reads pixels", attack_rasters_read),
    ("chunk guards agree", attack_chunk_guards_agree),
    ("no new chunk reads severity", attack_severity_readers),
    ("recorded checksums match", attack_checksums),
    ("chunk labels unique and cited", attack_chunk_labels_unique),
    ("session restore point exists", attack_restore_point),
]


def main():
    base = ev.load_baseline()
    if not base:
        print("no baseline; run --baseline first")
        return 1
    width = max(len(n) for n, _ in ATTACKS)
    blind, untested = [], []
    for name, fn in ATTACKS:
        try:
            status, note = fn(base)
        except Exception as exc:                          # noqa: BLE001
            status, note = None, f"attack raised {type(exc).__name__}: {exc}"
        if status is None:
            mark, verdict = "  --  ", "not attacked"
            untested.append(name)
        elif status in ("fail", "blocked"):
            mark, verdict = "  ok  ", f"caught it ({status})"
        else:
            mark, verdict = " BLIND", "did not notice"
            blind.append(name)
        print(f"{mark} {name:<{width}}  {verdict}: {note}")
    print(f"\n{len(ATTACKS)} attacks, {len(blind)} checks blind, "
          f"{len(untested)} not attacked")
    return 1 if blind else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
