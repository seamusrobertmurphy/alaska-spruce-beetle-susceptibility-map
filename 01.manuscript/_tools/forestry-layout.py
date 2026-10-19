"""Lays a rendered Word manuscript out as Forestry's general instructions ask.

Run on the rendered file after the render and before landscape-tables.py:
  python3 _tools/forestry-layout.py manuscript_submission.docx

The journal asks that tables be typed on separate pages and collected at the end of the text, that their
approximate position be indicated in the page margin, that figure captions be provided with the alt text under each legend, and that figures travel as separate files. Quarto puts
every table and figure in line, so this script moves each one out of the body, leaves a Word comment in the
margin at the paragraph it followed ("Table 1 near here", "Figure 2 near here"), and appends after the
References the tables and then the figures with their captions, each on its own page; the TIFF files under
03.outputs/figures are the separate figure files the journal asks for. The headings Supplementary material and References start
new pages, as Seamus set by hand on 2026-10-19.
"""
import copy, datetime, os, re, shutil, sys, tempfile, zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
q = lambda tag: f"{{{W}}}{tag}"

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    names = z.namelist(); data = {n: z.read(n) for n in names}
root = etree.fromstring(data["word/document.xml"])
body = root.find(q("body"))
kids = list(body)
text = lambda el: "".join(t.text or "" for t in el.iter(q("t")))
style = lambda p: (p.find(f"{q('pPr')}/{q('pStyle')}").get(q("val")) if p.find(f"{q('pPr')}/{q('pStyle')}") is not None else "")
cap_re = re.compile(r"^(Table|Figure)[\s ]+(\d+)[.:]")

def ppr(p):
    pp = p.find(q("pPr"))
    if pp is None:
        pp = etree.SubElement(p, q("pPr")); p.insert(0, pp)
    return pp

def page_break_before(p):
    pp = ppr(p)
    if pp.find(q("pageBreakBefore")) is None:
        pb = etree.Element(q("pageBreakBefore"))
        # pageBreakBefore sits after pStyle and keepNext in the schema order; placing it right after pStyle is valid
        ps = pp.find(q("pStyle"))
        if ps is not None: ps.addnext(pb)
        else: pp.insert(0, pb)

comments = []  # (id, text)
def add_comment(anchor, note):
    cid = str(len(comments))
    runs = anchor.findall(q("r"))
    start = etree.Element(q("commentRangeStart")); start.set(q("id"), cid)
    end = etree.Element(q("commentRangeEnd")); end.set(q("id"), cid)
    ref = etree.Element(q("r")); cr = etree.SubElement(ref, q("commentReference")); cr.set(q("id"), cid)
    if runs:
        runs[0].addprevious(start); runs[-1].addnext(end); end.addnext(ref)
    else:
        anchor.append(start); anchor.append(end); anchor.append(ref)
    comments.append((cid, note))

# 1. find the blocks to move. Quarto puts each figure in a one-cell table holding the image and its caption,
#    followed by the alt text paragraph; a data table is a table without an image, with its caption inside it
#    (flextable) or in the paragraph before it (a pipe table).
figure_blocks, table_blocks = [], []   # each block: dict(elements=[...to remove], captions=[...to keep], label=str)
claimed = set()
for i, el in enumerate(kids):
    if el.tag != q("tbl"): continue
    if el.find(f".//{q('drawing')}") is not None:
        caps = [copy.deepcopy(p) for p in el.iter(q("p")) if style(p) == "ImageCaption"]
        elements = [el]
        if i + 1 < len(kids) and kids[i + 1].tag == q("p") and text(kids[i + 1]).startswith("Alt text:"):
            caps.append(kids[i + 1]); elements.append(kids[i + 1])
        lab = next((m for m in (cap_re.match(text(c)) for c in caps) if m), None)
        figure_blocks.append(dict(elements=elements, captions=caps, label=f"{lab.group(1)} {lab.group(2)}" if lab else "Figure", index=i))
    else:
        elements = [el]; lab = None
        prev = kids[i - 1] if i > 0 else None
        if prev is not None and prev.tag == q("p") and cap_re.match(text(prev)):
            elements.insert(0, prev); lab = cap_re.match(text(prev))
        if lab is None:
            lab = next((m for m in (cap_re.match(text(p)) for p in el.iter(q("p"))) if m), None)
        if i + 1 < len(kids) and kids[i + 1].tag == q("p") and not text(kids[i + 1]).strip() and kids[i + 1].find(f"{q('pPr')}/{q('sectPr')}") is None:
            elements.append(kids[i + 1])
        table_blocks.append(dict(elements=elements, captions=[], label=f"{lab.group(1)} {lab.group(2)}" if lab else "Table", index=i))
    for e in elements: claimed.add(id(e))

# 2. margin notes at the body paragraph each block followed (or, after a heading, the one it preceded), then remove the blocks
def is_body(p):
    return p.tag == q("p") and text(p).strip() and not style(p).startswith("Heading") and style(p) not in ("ImageCaption", "TableCaption") and id(p) not in claimed and not text(p).startswith("Alt text:")
for blk in figure_blocks + table_blocks:
    idx = kids.index(blk["elements"][0]); anchor = None
    for k in range(idx - 1, -1, -1):
        if kids[k].tag == q("p") and style(kids[k]).startswith("Heading"): break
        if is_body(kids[k]): anchor = kids[k]; break
    if anchor is None:
        for k in range(idx + 1, len(kids)):
            if is_body(kids[k]): anchor = kids[k]; break
    if anchor is not None: add_comment(anchor, f"{blk['label']} near here")
for blk in figure_blocks + table_blocks:
    for el in blk["elements"]:
        if el.getparent() is body: body.remove(el)

# 3. new pages for the headings Seamus set, then the figure caption sheet and the tables after the references
for p in body.findall(q("p")):
    if style(p) == "Heading1" and text(p).strip() in ("Introduction", "Supplementary material", "References"):  # the new pages Seamus set by hand on 2026-10-18 and 2026-10-19
        page_break_before(p)
    if style(p) == "Author" and text(p).strip():  # the blank line he left after the author block
        blank = etree.Element(q("p")); bp = etree.SubElement(blank, q("pPr")); bs = etree.SubElement(bp, q("pStyle")); bs.set(q("val"), "Author"); p.addnext(blank)
sect = body[-1] if body[-1].tag == q("sectPr") else None
def append(el):
    if sect is not None: sect.addprevious(el)
    else: body.append(el)
for blk in table_blocks:
    first = blk["elements"][0]
    if first.tag == q("p"):
        page_break_before(first)
    else:
        spacer = etree.Element(q("p")); page_break_before(spacer); append(spacer)
    for el in blk["elements"]: append(el)
for blk in figure_blocks:  # after the tables, each figure on its own page with its caption inside the figure table and the alt text under it; the TIFF files are the separate figure files
    spacer = etree.Element(q("p")); page_break_before(spacer); append(spacer)
    for el in blk["elements"]: append(el)

# 4. the comments part
cx = etree.Element(q("comments"), nsmap={"w": W})
now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
for cid, note in comments:
    c = etree.SubElement(cx, q("comment")); c.set(q("id"), cid); c.set(q("author"), "Seamus Murphy"); c.set(q("initials"), "SM"); c.set(q("date"), now)
    p = etree.SubElement(c, q("p")); r = etree.SubElement(p, q("r")); t = etree.SubElement(r, q("t")); t.text = note
data["word/comments.xml"] = etree.tostring(cx, xml_declaration=True, encoding="UTF-8", standalone=True)
rels = data["word/_rels/document.xml.rels"].decode("utf8")
if "comments.xml" not in rels:
    ids = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]
    rels = rels.replace("</Relationships>", f'<Relationship Id="rId{max(ids) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>')
    data["word/_rels/document.xml.rels"] = rels.encode("utf8")
ct = data["[Content_Types].xml"].decode("utf8")
if "comments+xml" not in ct:
    ct = ct.replace("</Types>", '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>')
    data["[Content_Types].xml"] = ct.encode("utf8")
if "word/comments.xml" not in names: names.append("word/comments.xml")
data["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
tmp = tempfile.mktemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(path)))
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n in names: z.writestr(n, data[n])
shutil.move(tmp, path)
print(f"{path}: {len(table_blocks)} tables and then {len(figure_blocks)} figures moved to the end on their own pages, {len(comments)} margin notes")
