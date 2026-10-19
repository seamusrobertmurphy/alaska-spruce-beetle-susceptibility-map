"""Builds README.md from the laid-out submission manuscript, so that the README's title, abstract, tables, figures and
data availability statement are the rendered manuscript's and cannot drift from it.

  python3 _tools/readme-from-docx.py ../03.outputs/submission/manuscript.docx ../03.outputs/submission/supplementary_material.docx ../README.md

Tables become GitHub pipe tables with the caption above, figures become the PNG copies in 03.outputs/figures at full
width with the caption below, and asterisks and pipes in cell text are escaped so GitHub does not read them as markup.
GitHub sizes a table to its content and ignores width attributes, so no width is set on a table.
"""
import html, re, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def blocks(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf8").split("<w:body>")[1]
    return re.findall(r"<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>", x, re.S)

def esc(s):
    return s.replace("\\", "\\\\").replace("*", "\\*").replace("|", "\\|").replace("<", "&lt;")

def ptext(p):
    """Paragraph text with italic runs as *text*, markup characters escaped."""
    out, ital = [], None
    for r in re.findall(r"<w:r[ >].*?</w:r>", p, re.S):
        t = "".join(html.unescape(s) for s in re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r))
        if not t: continue
        i = re.search(r'<w:i(?:\s+w:val="(?:true|1|on)")?\s*/>', r) is not None  # an explicit w:val="false" is not italic
        if i != ital and out and ital: out.append("*")
        if i and i != ital: out.append("*")
        out.append(esc(t)); ital = i
    if ital: out.append("*")
    s = "".join(out)
    return re.sub(r"\*(\s+)\*", r"\1", s).strip()

def style(p):
    m = re.search(r'<w:pStyle w:val="([^"]*)"', p); return m.group(1) if m else ""

def label(cap):
    return re.sub(r"^(Table|Figure)[\s ]+(S?\d+)\.", r"**\1 \2.**", cap)

def parse(path):
    items = []
    for b in blocks(path):
        if b.startswith("<w:tbl>"):
            paras = re.findall(r"<w:p[ >].*?</w:p>", b, re.S)
            cap = [ptext(p) for p in paras if style(p) == "ImageCaption"]
            if "<w:drawing>" in b:
                items.append(("figure", cap[0] if cap else ""))
                continue
            rows = []
            for tr in re.findall(r"<w:tr[ >].*?</w:tr>", b, re.S):
                cells = []
                for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S):
                    ps = [ptext(p) for p in re.findall(r"<w:p[ >].*?</w:p>", tc, re.S) if style(p) != "ImageCaption"]
                    cells.append("<br>".join(p for p in ps if p))
                rows.append(cells)
            items.append(("table", cap[0] if cap else "", rows))
        else:
            items.append(("p", style(b), ptext(b)))
    return items

def gfm_table(rows):
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    head = "| " + " | ".join(rows[0]) + " |"
    sep = "|" + "|".join(["---"] * n) + "|"
    return "\n".join([head, sep] + ["| " + " | ".join(r) + " |" for r in rows[1:]])

main, supp, dst = sys.argv[1:4]
m = parse(main); s = parse(supp)
title = next(o[2] for o in m if o[0] == "p" and o[1] == "Title")
h1 = [i for i, o in enumerate(m) if o[0] == "p" and o[1] == "Heading1"]
def section(name):
    i = next(i for i in h1 if m[i][2].strip() == name)
    j = i + 1; out = []
    while j < len(m) and not (m[j][0] == "p" and m[j][1] == "Heading1"):
        if m[j][0] == "p" and m[j][2]: out.append(m[j][2])
        j += 1
    return out
abstract = " ".join(section("Abstract"))
avail = " ".join(section("Data availability statement"))
tables = [o for o in m if o[0] == "table"]
figures = [o for o in m if o[0] == "figure"]
supp_text = [o[2] for o in s if o[0] == "p" and o[1] in ("BodyText", "FirstParagraph") and o[2] and not o[2].startswith("Alt text")]
supp_fig = [o for o in s if o[0] == "figure"]

L = [f"# {title}", "",
     "Manuscript prepared for submission to Forestry, An International Journal of Forest Research. The text, tables and figures below are read from the rendered manuscript of 2026-10-19, so they match it word for word and number for number.", "",
     "## Abstract", "", abstract, "", "## Figures", ""]
for n, (_, cap) in enumerate(figures, 1):
    L += [f'<img src="03.outputs/figures/figure{n}.png" width="100%" alt="Figure {n}">', "", label(cap), ""]
L += ["## Tables", ""]
for _, cap, rows in tables:
    L += [label(cap), "", gfm_table(rows), ""]
L += ["## Supplementary material", "", " ".join(supp_text), ""]
for n, (_, cap) in enumerate(supp_fig, 1):
    L += [f'<img src="03.outputs/figures/figureS{n}.png" width="100%" alt="Figure S{n}">', "", label(cap), ""]
L += ["## Data availability", "", avail, "",
      "## Reproduction", "",
      "The manuscript is executable. Every number, table and figure is computed at render time from `01.manuscript/manuscript.qmd` and the saved outputs in `03.outputs/`, and the heavy chunks are guarded so that a render reads their saved outputs rather than recomputing them. Render with `quarto render manuscript.qmd --to docx` from inside `01.manuscript/`. The inputs, their sources and their licences are recorded in `02.inputs/README.md`; the large rasters and the Sentinel-1 samples are not committed and are regenerable from the chunks that built them. R is the CRAN build at `/usr/local/bin/R` and Python is MacPorts `python3` 3.12.", ""]
open(dst, "w", encoding="utf8").write("\n".join(L))
print(f"{dst}: {len(tables)} tables, {len(figures)} figures, {len(supp_fig)} supplementary figure, abstract {len(abstract.split())} words")
