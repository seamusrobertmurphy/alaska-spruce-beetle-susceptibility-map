#!/usr/bin/env python3
"""Count the main text on the Journal of Pest Science measure.

The journal limits Original Research Papers to 7,000 words, all text excluding
tables, figure legends and the reference list. The count is taken from the
rendered page rather than the source, so inline code is counted as the number
it renders to and a chunk is not counted at all. Code cells, figures and their
captions, tables, the table of contents, the reference list and everything
from the Supplementary material heading onward are excluded. The abstract is
counted and reported on its own line, because the journal bounds it separately
at 150 to 250 words.

    python3 01.manuscript/_tools/word_count.py
"""
import os
import re
import sys

from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PAGE = os.path.join(ROOT, "01.manuscript", "manuscript.html")

EXCLUDE_TAGS = ("figure", "figcaption", "table", "nav", "script", "style")
EXCLUDE_SECTIONS = ("references", "supplementary-material")


def words(text):
    return len(re.findall(r"\S+", text))


def main():
    page = sys.argv[1] if len(sys.argv) > 1 else PAGE
    soup = BeautifulSoup(open(page, encoding="utf-8").read(), "lxml")
    for t in soup.find_all(EXCLUDE_TAGS):
        t.decompose()
    for cell in soup.select("div.cell"):
        cell.decompose()
    for sid in EXCLUDE_SECTIONS:
        sec = soup.find("section", id=sid)
        if sec:
            sec.decompose()
    abstract = soup.find("div", class_="abstract")
    n_abs = 0
    if abstract:
        title = abstract.find(class_="block-title")
        if title:
            title.decompose()
        n_abs = words(abstract.get_text(" "))
        abstract.decompose()
    main = soup.find("main", id="quarto-document-content")
    rows = [("Abstract", n_abs)]
    total = n_abs
    for sec in main.find_all("section", class_="level1"):
        head = sec.find(["h1", "h2"])
        name = head.get_text(" ").strip() if head else sec.get("id")
        n = words(sec.get_text(" "))
        rows.append((name, n))
        total += n
    for name, n in rows:
        print(f"{n:>7,}  {name}")
    print(f"{total:>7,}  total on the journal's measure (limit 7,000)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
