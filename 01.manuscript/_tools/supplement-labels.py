"""Closes the space Quarto puts between the supplement's label word and its number, so that Table S 1 reads Table S1 and Figure S 1 reads Figure S1.

Run on the rendered supplement after the render:
  python3 _tools/supplement-labels.py supplementary.docx

Quarto's crossref options tbl-title and fig-title set the words Table S and Figure S, and it then adds a non-breaking space before the number. The journal's own numbering is S1, so the space is removed in the Word XML, both when it sits in the same run as the label and when Quarto split it into its own run.
"""
import re, shutil, sys, tempfile, zipfile, os

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    names = z.namelist(); data = {n: z.read(n) for n in names}
x = data["word/document.xml"].decode("utf8")
before = x
x = re.sub(r"(Table S|Figure S) ", r"\1", x)
x = re.sub(r"(Table S|Figure S)(</w:t></w:r>(?:(?!</w:r>).)*?<w:t[^>]*>) ", r"\1\2", x, flags=re.S)
n = len(re.findall(r"(?:Table|Figure) S\d", re.sub(r"<[^>]+>", "", x)))
if x == before:
    sys.exit(f"{path}: no supplement label with a space found, file left unchanged")
data["word/document.xml"] = x.encode("utf8")
tmp = tempfile.mktemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(path)))
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n_ in names: z.writestr(n_, data[n_])
shutil.move(tmp, path)
print(f"{path}: {n} supplement labels now read S followed by the number")
