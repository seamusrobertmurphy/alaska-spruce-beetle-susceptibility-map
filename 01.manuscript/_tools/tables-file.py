"""Writes the tables of a laid-out Word manuscript to their own Word file, for the separate tables upload.

Run on the laid-out manuscript, after forestry-layout.py and landscape-tables.py:
  python3 _tools/tables-file.py manuscript_submission.docx tables.docx

The laid-out manuscript ends with the tables on their own pages and then the figures. This keeps the body
from the first table's page to the last table's page, with the section breaks that turn wide tables
landscape, and drops everything else, the margin comments included, so the new file holds only Table 1
to the last table with their captions.
"""
import os, re, shutil, sys, tempfile, zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
q = lambda tag: f"{{{W}}}{tag}"
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as z:
    names = z.namelist(); data = {n: z.read(n) for n in names}
root = etree.fromstring(data["word/document.xml"]); body = root.find(q("body")); kids = list(body)
text = lambda el: "".join(t.text or "" for t in el.iter(q("t")))
is_fig = lambda el: el.tag == q("tbl") and el.find(f".//{q('drawing')}") is not None
is_tab = lambda el: el.tag == q("tbl") and el.find(f".//{q('drawing')}") is None
tabs = [i for i, el in enumerate(kids) if is_tab(el)]
figs = [i for i, el in enumerate(kids) if is_fig(el)]
if not tabs: sys.exit(f"{src}: no table found")
i0 = tabs[0]
while i0 > 0 and kids[i0 - 1].tag == q("p") and (not text(kids[i0 - 1]).strip() or re.match(r"^Table[\s ]+\d", text(kids[i0 - 1]))) and "Bibliography" not in etree.tostring(kids[i0 - 1]).decode():
    i0 -= 1
i1 = figs[0] if figs else len(kids) - 1
while i1 > tabs[-1] + 1 and kids[i1 - 1].tag == q("p") and not text(kids[i1 - 1]).strip():
    i1 -= 1
keep = kids[i0:i1]
for el in kids:
    if el.tag != q("sectPr"): body.remove(el)
sect = body.find(q("sectPr"))
for el in keep:
    for cr in el.iter(q("commentRangeStart")): cr.getparent().remove(cr)
    for cr in el.iter(q("commentRangeEnd")): cr.getparent().remove(cr)
    for r in list(el.iter(q("r"))):
        if r.find(q("commentReference")) is not None: r.getparent().remove(r)
    sect.addprevious(el)
first = next((el for el in body if el.tag == q("p")), None)
if first is not None:
    pp = first.find(q("pPr"))
    if pp is not None:
        for pb in pp.findall(q("pageBreakBefore")): pp.remove(pb)
data["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
rels = data["word/_rels/document.xml.rels"].decode("utf8")
data["word/_rels/document.xml.rels"] = re.sub(r'<Relationship [^>]*Target="comments.xml"[^>]*/>', "", rels).encode("utf8")
ct = data["[Content_Types].xml"].decode("utf8")
data["[Content_Types].xml"] = re.sub(r'<Override PartName="/word/comments.xml"[^>]*/>', "", ct).encode("utf8")
names = [n for n in names if n != "word/comments.xml"]
tmp = tempfile.mktemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(dst)) or ".")
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n in names: z.writestr(n, data[n])
shutil.move(tmp, dst)
print(f"{dst}: {len(tabs)} tables kept from element {i0} to {i1 - 1} of {len(kids)}")
