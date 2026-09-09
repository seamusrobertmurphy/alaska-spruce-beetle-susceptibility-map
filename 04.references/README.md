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

## Search corpus, 2026-09-08

Twenty entries added by the literature search of 2026-09-08, recorded in full in
`02.inputs/derived/literature_screening.csv`, which carries all 115 screened records with
each one's strand, decision and reason. Every entry below was verified against CrossRef by
content negotiation on its DOI before it entered `references.bib`. No PDF was retrieved.

Read status is the important column here and it is uniform. **None of these twenty was read
in full.** Fifteen were read at abstract level, retrieved from OpenAlex on 2026-09-08, and
the claims made about them in the manuscript are held to what the abstract states. Five
returned no abstract from either OpenAlex or Semantic Scholar, namely `Meigs_2011`,
`Meddens_2013`, `Senf_2015`, `DeRose_2011` and `DeRose_2012`, and those five are cited only
for the claim their title states outright, grouped in a parenthetical, never paraphrased.

Before any of these carries a load-bearing claim, a specific threshold, a quoted phrase or a
reported effect size, the paper is retrieved and read, and this table is rewritten with what
the reading found. That is the same standard the seed corpus was held to and the reason
`Bright_2020` above records two corrected misreadings.

| Key | Identity | Read status |
|---|---|---|
| `Patacca_2022` | Global Change Biology, disturbance impacts on European forests 1950 to 2019 | Abstract only, 2026-09-08 |
| `White_2017` | Remote Sensing of Environment, 25 years of annual national disturbance and recovery for Canada | Abstract only, 2026-09-08 |
| `Meigs_2011` | Remote Sensing of Environment, Landsat time series for bark beetle and defoliator mortality | Title only, no abstract available |
| `Meddens_2013` | Remote Sensing of Environment, single-date against multi-date detection of beetle-caused mortality | Title only, no abstract available |
| `Huo_2021` | Remote Sensing of Environment, early stress detection and a new index for *Ips typographus* | Abstract only, 2026-09-08 |
| `Abdullah_2018` | Remote Sensing in Ecology and Conservation, Sentinel-2 green-attack mapping | Abstract only, 2026-09-08 |
| `Senf_2015` | Remote Sensing of Environment, spectral-temporal patterns of defoliator and bark beetle disturbance | Title only, no abstract available |
| `Morris_2016` | Journal of Applied Ecology, priority questions on bark beetle impacts | Abstract only, 2026-09-08 |
| `Dalponte_2022` | Remote Sensing, Sentinel-2 outbreak mapping at crown level in the Italian Alps | Abstract only, 2026-09-08 |
| `Candotti_2022` | Remote Sensing, multi-temporal Sentinel-2 framework for wind and bark beetle damage | Abstract only, 2026-09-08 |
| `Yuan_2021` | IEEE JSTARS, self-supervised transformer pretraining for satellite image time series | **Read in full 2026-09-08**, 14 pages. Cited for label scarcity, and the paper states it verbatim: "deep learning methods suffer from overfitting when labeled data are scarce". |
| `Kong_2018` | Remote Sensing, recurrent networks for online disturbance detection in image time series | Abstract only, 2026-09-08 |
| `Tang_2022` | IEEE GRSL, channel attention over a temporal convolutional network | Abstract only, 2026-09-08 |
| `Miller_2024` | IEEE GRSM, review of deep learning for satellite image time series | **Read in full 2026-09-08**, 38 pages, retrieved from arXiv. Cited only as the survey of the field, which is what it is. |
| `Hall_2016` | The Canadian Entomologist, review of remote sensing of forest pest damage | **Read in full 2026-09-08**, 61 pages. The claim it carries is on its first page: "aerial survey consistency and spatial coverage may be insufficient for detailed monitoring across Canada's vast forest-land base. Remote sensing can augment these methods". The manuscript sentence was tightened to keep the hedge "may be", which the first draft had dropped. |
| `Hart_2017` | Ecology, summer and winter drought driving *Dendroctonus rufipennis* outbreak | Abstract only, 2026-09-08 |
| `DeRose_2012` | Forest Science, spatial and temporal dynamics of Engelmann spruce mortality | Title only, no abstract available |
| `DeRose_2011` | Remote Sensing of Environment, dendrochronology with a disturbance index | Title only, no abstract available |
| `Housman_2018` | Remote Sensing, insect and disease survey data against satellite products. The search resolved a preprints.org record first; the peer-reviewed version at doi 10.3390/rs10081184 is what entered the bibliography | Abstract only, 2026-09-08 |
| `Marvasti_Zadeh_2023` | ACM Computing Surveys, review of early bark beetle detection by remote sensing and machine learning | Abstract only, 2026-09-08 |

### Retrieval attempt, 2026-09-08

Fifteen of the twenty are open access by Unpaywall, but only three could be retrieved by
script. Wiley, ScienceDirect, MDPI, Oxford University Press and the ACM Digital Library all
returned an HTML bot challenge in place of the PDF, and every one of those was caught by
checking that the file begins with `%PDF` rather than by trusting the file extension, which
is the same guard the chip fetcher needed. The five with no open version at all remain
`Meigs_2011`, `Meddens_2013`, `Senf_2015`, `DeRose_2011` and `DeRose_2012`, all paywalled.

Retrieving the remaining seventeen needs either institutional access or a browser session,
so it is not something a script can finish. Until then their rows above stand as written.
