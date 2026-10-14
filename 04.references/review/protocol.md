# Review protocol

Written 2026-10-14, before any query ran, for `deep-learn-alaska-spruce-beetle`. Follows `library-science/protocols/literature-review.md`. Frozen by the commit that adds it. Nothing above "Deviations" is edited after that commit.

## Objectives


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

