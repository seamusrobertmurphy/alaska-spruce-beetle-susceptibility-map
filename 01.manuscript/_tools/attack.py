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
    """Move a block row and confirm the lock check notices."""
    with Perturb(ev.SAMPLE_CSV) as p:
        lines = p.before.decode().split("\n")
        if len(lines) < 3:
            return None, "sample table too short to perturb"
        lines[2] = lines[2].replace(",", ",9", 1)
        p.write("\n".join(lines).encode())
        return ev.check_sample_lock(base)[0], "one coordinate changed in a block row"


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



def attack_display_budget(base):
    """Add a table to the main text and confirm the ratchet notices.

    The budget check compares against the recorded count rather than against
    the target, so the attack has to add an item, not fail to remove one.
    """
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^```\{r\}\n#\|\s*label: tbl-\S+", text, re.M)
        if not m:
            return None, "no table chunk found to duplicate"
        block = "```{r}\n#| label: tbl-attack-extra\n1\n```\n\n"
        p.write((text[:m.start()] + block + text[m.start():]).encode())
        return ev.check_display_budget(base)[0], "one table added to the main text"


def attack_displaced_tables_kept(base):
    """Delete a displaced table outright rather than moving it."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        # Whichever name the table currently carries: a table already moved to
        # the supplement is labelled supp-, and an attack that only knows the
        # tbl- name stops attacking the moment the first move lands, which
        # leaves the check untested exactly when it starts mattering.
        names = [n for lab in ev.DISPLACED_TABLES
                 for n in (lab, lab.replace("tbl-", "supp-"))]
        m = lab = None
        for n in names:
            m = re.search(r"^```\{[^}]*\}\n#\|\s*label: " + re.escape(n) +
                          r"\b.*?^```\n", text, re.S | re.M)
            if m:
                lab = n
                break
        if not m:
            return None, "no displaced table chunk found to delete"
        p.write((text[:m.start()] + text[m.end():]).encode())
        return ev.check_displaced_tables_kept(base)[0], f"{lab} deleted"


def attack_cross_references(base):
    """Add a second reference to a table already cited once."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        cited = [lab for lab, n in
                 ((l, len(re.findall(r"@" + re.escape(l) + r"\b",
                                     ev.prose_of(text))))
                  for l in {m.group(1) for m in
                            ev.DISPLAY_LABEL.finditer(text)}) if n == 1]
        if not cited:
            return None, "no singly cited display item to duplicate"
        lab = sorted(cited)[0]
        m = re.search(r"@" + re.escape(lab) + r"\b", text)
        p.write((text[:m.end()] + f" and again in @{lab}" +
                 text[m.end():]).encode())
        return ev.check_cross_references(base)[0], \
            f"{lab} referenced a second time"


def attack_no_assistant_traces(base):
    """Add a placeholder to the prose and confirm the count is watched."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^# Introduction\n", text, re.M)
        if not m:
            return None, "Introduction heading not found"
        p.write((text[:m.end()] + "\n[Pending: an attack placeholder.]\n" +
                 text[m.end():]).encode())
        return ev.check_no_assistant_traces(base)[0], "one placeholder added"


def attack_house_punctuation(base):
    """Lengthen a heading past three words."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^## Study area$", text, re.M)
        if not m:
            return None, "the study area heading was not found"
        p.write((text[:m.start()] + "## Study area and its wider setting" +
                 text[m.end():]).encode())
        return ev.check_house_punctuation(base)[0], "a heading run to six words"



def attack_code_is_shown(base):
    """Hide one chunk's code and confirm the house rule notices."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^#\|\s*label: tbl-\S+$", text, re.M)
        if not m:
            return None, "no table chunk found to hide"
        p.write((text[:m.end()] + "\n#| echo: false" +
                 text[m.end():]).encode())
        return ev.check_code_is_shown(base)[0], "one chunk hidden"


def attack_results_computed(base):
    """Turn a computed table back into a shell of pending values."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^#\|\s*label: tbl-inputs$", text, re.M)
        if not m:
            return None, "tbl-inputs not found to shell"
        p.write((text[:m.end()] + '\nx <- "pending"' +
                 text[m.end():]).encode())
        return ev.check_results_computed(base)[0], "one table turned to a shell"


def attack_apparatus_present(base):
    """Drop a pre-registered test from the document."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        broken = re.sub("Holm", "the correction", text, flags=re.I)
        if broken == text:
            return None, "Holm was not named to remove"
        p.write(broken.encode())
        return ev.check_apparatus_present(base)[0], "Holm correction removed"


def attack_no_first_person(base):
    """Add a first-person sentence to the prose."""
    with Perturb(ev.QMD) as p:
        text = p.before.decode()
        m = re.search(r"^# Introduction\n", text, re.M)
        if not m:
            return None, "Introduction heading not found"
        p.write((text[:m.end()] + "\nWe report our findings here.\n" +
                 text[m.end():]).encode())
        return ev.check_no_first_person(base)[0], "a first-person sentence added"


def attack_venue_requirements(base):
    """Point the check at a directory holding no record of the guide."""
    real = ev.STANDARDS
    ev.STANDARDS = real + "-does-not-exist"
    try:
        return ev.check_venue_requirements_on_file(base)[0], \
            "standards directory redirected"
    finally:
        ev.STANDARDS = real


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
    ("chunk labels unique", attack_chunk_labels_unique),
    ("main text within its display budget", attack_display_budget),
    ("displaced tables kept, not deleted", attack_displaced_tables_kept),
    ("display items cross-referenced once", attack_cross_references),
    ("no placeholder left in the prose", attack_no_assistant_traces),
    ("headings and dashes follow the house rule", attack_house_punctuation),
    ("every chunk shows its code", attack_code_is_shown),
    ("results tables carry computed values", attack_results_computed),
    ("pre-registered apparatus still named", attack_apparatus_present),
    ("prose carries no first person", attack_no_first_person),
    ("venue requirements read and recorded", attack_venue_requirements),
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
