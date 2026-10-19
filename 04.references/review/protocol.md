# Review protocol

Written 2026-10-14, before any query ran, for `alaska-spruce-beetle-susceptibility-map` (named `deep-learn-alaska-spruce-beetle` until 2026-10-19). Follows `library-science/protocols/literature-review.md`. Frozen by the commit that adds it. Nothing above "Deviations" is edited after that commit.

## Objectives

Set by Seamus on 2026-10-14 and recorded verbatim in the project's working notes under Resume 2026-10-14. The study uses the crown labels and severity map of Zwieback et al. (2024) to validate that the pre-outbreak Sentinel-1 radar level separates the white spruce stands the outbreak killed from living stands, then maps susceptible spruce stands across Alaska for the forest managers preparing their stands against the next outbreak, testing the statewide map where the beetle has been and shrinking the extent if the accuracy fails. The review is built around what the saved results found, that the stands the beetle killed were the tallest and largest.

1. Validate, against the crown labels and the severity map of Zwieback et al. (2024), that the Sentinel-1 radar level before the outbreak and satellite canopy height rank the stands the outbreak killed above the stands it left alive.
2. Map the susceptible spruce stands across Alaska from those measures and test the map against the aerial detection survey and the Forest Inventory and Analysis plots of the regions the outbreak has reached, with the Tanana valley as the unattacked comparison.
3. Establish from prior work that the spruce beetle attacks the tallest and largest spruce first, and which tree and stand attributes predicted susceptibility.

## Questions

1. Which tree and stand attributes predicted spruce beetle attack and mortality, and did the beetle take the larger and taller spruce first? Population *Dendroctonus rufipennis* on *Picea*, concept host selection by tree size, growth, vigour and stand structure, including hazard and risk ratings, context North American spruce forests, outbreak and endemic.
2. What remotely sensed data and methods have mapped spruce beetle damage or susceptibility, and with what accuracy and at what support? Population spruce beetle outbreaks, concept aerial survey, optical satellite, radar and canopy height mapping of damage or susceptible stands, context North America.
3. Novelty. Has a regional or statewide map of spruce stands susceptible to the spruce beetle been made from satellite structure data, radar or canopy height, without a field cruise, and tested against the outbreak? Population spruce beetle susceptibility, concept satellite radar or canopy height mapping, context any region.

## Adjudication

1. If the retained studies report that attack or mortality fell with tree size, or that stand hazard ratings did not use diameter, basal area or spruce share, the claim that a map of tall large-spruce stands is a susceptibility map is withdrawn and the Introduction states the disagreement. If the studies agree that larger and taller spruce were attacked first, the attribute table carries that direction and the hypothesis follows from it.
2. If a prior study mapped spruce beetle damage from Sentinel-1 or from canopy height at the stand scale with a stated accuracy, that study becomes the comparator and the Discussion reports this study against it. If none did, the Introduction states that no such accuracy had been reported.
3. If a prior study produced a regional susceptibility map from satellite structure data and tested it against the outbreak, this study is a replication and says so. If the prior maps rest on field hazard ratings or on occurrence models, this study is new work and the gap is stated as such.

## Criteria

1. Document types: peer-reviewed articles, reviews and book chapters, and United States Forest Service and Canadian Forest Service research papers, general technical reports, research notes and leaflets, which are the primary record of the Alaska and Rocky Mountain spruce beetle work of 1950 to 2000.
2. Published 1954 to 2026, opening at 1954 because Massey and Wygant (1954) is the first systematic account of spruce beetle host selection in the United States literature.
3. Language: English.
4. Bears on at least one question, meaning the record reports an attribute of the attacked tree or stand (question 1), a remotely sensed map or detection of spruce beetle damage or susceptibility (question 2), or a susceptibility map from satellite structure data (question 3).

Exclusions use the codes in the protocol. Records on other *Dendroctonus* species are `wrong-population` unless the record compares them with the spruce beetle or is cited for a mechanism the spruce beetle literature itself relies on; such a record is marked `include` with the attribute `mechanism`.

## Sources

1. `library-science`, searched with the `review-store` chunk.
2. Semantic Scholar bulk search, with the `review-semantic-scholar` chunk.
3. OpenAlex, with the `review-openalex` chunk, as a third strand because the Semantic Scholar index is thin for Forest Service reports before 1990.
4. Grey literature by hand: the United States Forest Service Treesearch repository for Forest Service research papers, general technical reports and the Forest Insect and Disease Leaflet on the spruce beetle, and the Alaska Forest Health Conditions reports for the extent of the current outbreak.

Search terms are selected in `04.references/review/search-terms.csv`, from candidates the `review-terms` chunk drew from the manuscript's title and keywords, and committed with this file. The queries are built from that selection by the `review-queries` chunk in `01.manuscript/manuscript.qmd`. The reader is one person, Seamus Murphy's agent working under his direction, and no second reader checks the decisions.

## Deviations

2026-10-14. The Treesearch search page at research.fs.usda.gov returned the same four unrelated publications for every keyword query, so the grey literature was not found through it. The Forest Service research papers and the leaflet were fetched by their direct report URLs (fs.usda.gov/pnw/pubs and fs.usda.gov/foresthealth/docs/fidls), and the Rocky Mountain reports of 1954 to 1977 as National Agricultural Library scans on archive.org. Records found this way carry the route `grey` in the screening table only where no strand had retrieved them; Massey and Wygant (1954), Schmid and Frye (1976, 1977), Hard and Holsten (1985), Holsten and Hard (2001) and the leaflet had all been retrieved by a strand, so no grey row was added.

2026-10-14. Semantic Scholar returned no reference list for any of the four Alaska papers of 1983 to 1994 used as chase seeds, only their citing papers, so the backward chase from them is a gap recorded in the synthesis. The OpenAlex strand searched titles and abstracts (`title_and_abstract.search`) rather than full text, to match the scope of the Semantic Scholar strand; the first run with the full-text `search` parameter was discarded before any record was screened.

2026-10-14. One hundred and sixty records from the chase were appended to the screening table after the three strands had been screened, with their route and seed recorded, and screened under the same criteria.

2026-10-14, 22:40. The working title was replaced by the title Seamus chose, "A statewide spruce beetle susceptibility map for Alaska from Sentinel-1 radar and satellite canopy height, validated against crown-scale mortality in the Susitna valley". Every selected term in `search-terms.csv` still appears in the title or the keywords, so the `review-queries` chunk passes unchanged and no query was rerun.

2026-10-16. Correction to the first entry of 2026-10-14. That entry stated that Massey and Wygant (1954), Schmid and Frye (1977), Holsten and Hard (2001) and the spruce beetle leaflet had been retrieved by a strand, so that no grey row was needed. A check of the screening table on 2026-10-16 found only Schmid and Frye (1976) and Hard and Holsten (1985) there. The four missing reports and Werner and Holsten (1997) were added with the route `grey`.

2026-10-16. Four sources outside the population of the questions, Dobson et al. (1992) and Santoro and Cartus (2018) on how radar backscatter follows forest biomass, and Hollaus and Vreugdenhil (2019) and Hechtl et al. (2025) on radar detection of bark beetle damage, were added with the route `hand-attribute` because rows of the attribute table rest on them.

2026-10-16. Three `full_text` flags entered on 2026-10-14 claimed reading that had not happened, Bakaj et al. (2016) and Woodward et al. (2018), which were read only in abstract, and Ye et al. (2021), read only by title. They were corrected, and two doubled-title rows from Semantic Scholar that had been marked include were marked `duplicate`.

2026-10-16. The attribute table was rebuilt with one row per measure the study entered, each resting on the literature alone, after the version of 2026-10-14 cited the study's own results as the reasoning for four rows.
