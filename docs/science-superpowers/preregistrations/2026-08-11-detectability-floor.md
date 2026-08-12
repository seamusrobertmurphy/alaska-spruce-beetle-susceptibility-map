# Pre-registration: detectability floor for spruce beetle mortality from open satellite time series

**Frozen at commit:** (the commit adding this file is the timestamp)
**Question doc:** docs/science-superpowers/questions/2026-08-10-detectability-floor.md
**Analysis plan:** docs/science-superpowers/plans/2026-08-11-detectability-floor-plan.md
**Status of outcome data at freeze:** no severity label exists yet (digitisation not begun); the Zwieback severity rasters are on disk but no value has been read, summarised, plotted, or joined to any predictor; predictor composites exist and have been inspected only via their n_clear data-density layer.

## Hypotheses

- H1-H0: temporal deep learning does not exceed the SWIR change baseline in detection skill within the 0.01-0.10 severity stratum.
- H1 (directional): TempCNN achieves higher recall at 0.90 precision than the SWIR change baseline in the 0.01-0.10 stratum.
- H2-H0: interval-censored onset supervision does not reduce onset error relative to single-epoch point supervision.
- H2 (directional): TempCNN trained with the marginal-likelihood loss over each stand's onset bracket achieves lower onset MAE than the same architecture trained on bracket-midpoint point labels.

## Primary analyses (exact)

- Unit: 90 m stand cell on the Zwieback reference grid, UTM 5N.
- Outcome: stand-cell areal severity fraction from our crown labels (2023 epoch defines the endpoint severity; 2020 epoch and Zwieback label dates define onset brackets). Severity strata (fixed): 0-0.01, 0.01-0.03, 0.03-0.05, 0.05-0.10, 0.10-0.20, >0.20. Detection positive class: severity >= 0.01.
- Predictors: annual July-August composites 2014-2025 (Sentinel-2 CS+ quality mosaics 2019-2025; Landsat QA-masked composites 2014-2018), bands red/NIR/SWIR1/SWIR2 + n_clear + sensor flag; static IFSAR terrain and conifer fraction.
- Models: TempCNN (primary; Pelletier 2019 architecture, no pooling), Transformer encoder (secondary). Subsequences: 10-year windows, onset position randomized in training; two heads (severity class; onset year, marginal-likelihood over the censoring bracket). Hyperparameters tuned only on training-internal validation splits; tuning grid fixed in the plan's config files before training.
- Baseline: per-cell SWIR2 change, mean(2019-2021) minus mean(2014-2016), logistic model for detection and cubic-calibrated regression for severity, fitted on training folds only.
- Cross-validation: 8 contiguous spatial folds fixed by 05.scripts/03_sample_blocks.R (fixed seed, committed before any label work); the Talkeetna to Byers Lake footprint is wholly inside one fold; independent Zwieback-raster evaluation uses only models whose training excluded that fold.
- H1 test: per-fold recall at precision 0.90 (operating point selected on the training folds' PR curve, applied unchanged to the test fold), paired difference TempCNN minus baseline within the 0.01-0.10 stratum; one-sided Wilcoxon signed-rank across the 8 folds; block bootstrap (resampling folds, 10,000 draws) for the 95% CI.
- H2 test: per-fold onset MAE (years), paired difference interval-trained minus point-trained TempCNN; one-sided Wilcoxon signed-rank across folds.

## Predictions

- H1: positive difference, planning magnitude ~0.3 (deep 0.4-0.5, baseline 0-0.15; sources: Perbet 2024/2025 omission rates; Zwieback 2024 sub-0.1 null).
- H2: negative MAE difference (interval better), magnitude unspecified; direction only.

## Decision rules

- Confirm H1 iff Holm-corrected one-sided p < 0.05 AND the bootstrap 95% CI on the mean fold difference lies entirely above zero. Disconfirm (H0 stands) otherwise. A significant result with CI overlapping zero is reported as inconclusive, not confirmatory.
- Confirm H2 iff Holm-corrected one-sided p < 0.05 AND CI entirely below zero for the MAE difference.
- Detectability floor (reported, not tested): the lowest stratum in which a model's recall at 0.90 precision is >= 0.50. The claim "the floor was lowered" requires H1 confirmed AND floor(TempCNN) < 0.10.
- Disconfirming results are publishable as stated in the manuscript's discussion; no reframing.

## Sample size and stopping

- 160 label blocks of 512 m, stratified by conifer fraction and survey damage history, fixed seed; 8 folds. No extension, no exclusion of blocks after outcomes are seen except pre-specified QC (annotator disagreement unresolved by adjudication; imagery void), logged with reasons.
- Power: with planning effect 0.3 and fold SD 0.15, one-sided Wilcoxon at n=8 exceeds 0.95 power (sign consistency near-certain); stated in the plan.

## Multiplicity

- Two confirmatory tests (H1, H2), Holm correction within the family. Transformer results, 7-year windows, Landsat-only runs, anchored-window variant, 30 m support, and all Theil's U decompositions are secondary/descriptive. The retrospective green-stage look-back and the annual progression comparison are exploratory and will be labelled so.

## Falsifiability check

H1 is disconfirmed by a fold-wise difference distribution centred at or below zero; concretely, if the baseline matches the deep model's low-severity recall (as it would if SWIR change carries more low-severity signal than Zwieback's single-epoch analysis could see), H1 fails. H2 is disconfirmed if bracket supervision adds nothing over midpoints, which is plausible if the true onset distribution is tight within brackets.

## Deviations

Any deviation is documented in the manuscript and renders the affected analysis exploratory.
