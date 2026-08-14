# 04.references, source manifest

Every source in this folder is recorded here: what it is, where it came from, whether it
is peer-reviewed, and whether it has been read. PDFs are not committed to git; this
manifest is how a fresh clone knows what to retrieve. Verify each bibliographic record
against CrossRef before it enters `references.bib`.

## literature/

### Seed corpus

Supplied by Seamus 2026-08-10. The block below is **stale as of 2026-08-14**: it was
written before the corpus was read, lists three of the eight PDFs on disk, and its
"none yet read, none yet verified" statement is contradicted by the project record in
2026-08-10/11 and every `references.bib` entry CrossRef-verified. The rows are left
verbatim rather than rewritten from memory; rebuilding them is a separate job.

| File | Presumed identity (from filename, unverified) | Status |
|---|---|---|
| `Chatri-Khetri 2024 Enhancing individual tree mortality mapping...pdf` | Chatri-Khetri 2024, individual tree mortality mapping: models, data modalities, classification taxonomy | Unread |
| `Kautz et al 2024 Early detection of bark beetle Ips typographus infestations by remote sensing.pdf` | Kautz et al. 2024, early detection of *Ips typographus* by remote sensing. Note: European spruce bark beetle, not *Dendroctonus rufipennis* | Unread |
| `Perbet 2024 Evaluating deep learning methods applied to Landsat time series subsequences...pdf` | Perbet 2024, deep learning on Landsat time-series subsequences for boreal forest disturbance detection and classification | Unread |

### Later additions

| File | Identity | Provenance | Citability | Read status |
|---|---|---|---|---|
| `Bright et al 2020 Mapping Multiple Insect Outbreaks across Large Regions Annually Using Landsat Time Series Data.pdf` | Bright, B.C., Hudak, A.T., Meddens, A.J.H., Egan, J.M., Jorgensen, C.L. (2020) *Remote Sensing* 12(10):1655, doi 10.3390/rs12101655. Bark beetle and defoliator mortality mapped annually 1984-2018 across three Rocky Mountain sites from Landsat, high-resolution crowns as reference, random forest severity within threshold-classified disturbed pixels. | Supplied by Seamus 2026-08-13. Published by MDPI 21 May 2020 under CC-BY 4.0; received 27 April 2020, accepted 19 May 2020. Bib entry taken from CrossRef content negotiation on the DOI 2026-08-14 and each field checked against the PDF title page and running footer. | Peer-reviewed journal article, citable. Key `@Bright_2020`. | **Read in full 2026-08-14** from the extracted text layer (`pypdf`, 20 pages, clean). Serves as the published state of the art for the H1 comparator; see `tasks/2026-08-14-baseline-amendment.md` and the 2026-08-14 pre-registration amendment draft. Two standing misreadings corrected on reading: it does not run the LandTrendr algorithm (only LandTrendr's GEE preprocessing functions, section 2.4.2 p. 7), and it does not train on aerial detection survey polygons (they enter only at section 2.7 as independent comparison). |

## reports/

Empty.

## standards/

Empty.
