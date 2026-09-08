#!/usr/bin/env python3
"""Prove an edit to the manuscript touched prose only.

Splits the document into code chunks and everything else, and fingerprints the
chunks. A prose edit that changes a single byte inside a chunk fails, so the
analysis cannot be altered by a wording pass.

    python3 prose_guard.py --record      fingerprint the chunks as they stand
    python3 prose_guard.py               confirm no chunk has moved
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QMD = os.path.join(ROOT, "01.manuscript", "manuscript.qmd")
STORE = os.path.join(os.path.dirname(__file__), ".prose_guard.json")

# The YAML header is configuration, not prose, and is frozen with the chunks.
CHUNK = re.compile(r"^```\{.*?^```", re.S | re.M)
YAML = re.compile(r"\A---\n.*?\n---\n", re.S)


def fingerprints():
    text = open(QMD, encoding="utf-8").read()
    parts = [m.group(0) for m in YAML.finditer(text)]
    parts += [m.group(0) for m in CHUNK.finditer(text)]
    return [hashlib.sha256(p.encode()).hexdigest()[:16] for p in parts]


def main():
    fps = fingerprints()
    if "--record" in sys.argv:
        json.dump(fps, open(STORE, "w"))
        print(f"recorded {len(fps)} frozen regions")
        return 0
    if not os.path.exists(STORE):
        print("no record; run --record first")
        return 1
    want = json.load(open(STORE))
    if fps == want:
        print(f"{len(fps)} frozen regions unchanged")
        return 0
    if len(fps) != len(want):
        print(f"FAIL region count moved, {len(want)} to {len(fps)}")
        return 1
    moved = [i for i, (a, b) in enumerate(zip(fps, want)) if a != b]
    print(f"FAIL {len(moved)} frozen regions changed, at index "
          + ", ".join(str(i) for i in moved[:8]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
