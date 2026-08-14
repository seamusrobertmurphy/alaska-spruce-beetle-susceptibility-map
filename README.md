# Multi-year temporal deep learning and open satellite data lower the detectability floor for low-severity spruce beetle mortality in Southcentral Alaska

## Abstract

Spruce beetle (*Dendroctonus rufipennis*) has killed spruce across Southcentral Alaska since about 2016, yet roughly ninety percent of the mortality sits in stands of areal severity below 0.05, beneath the detection floor of conventional Landsat change analysis, and the aerial survey record understates exactly this dispersed, low-severity damage. We test whether temporal deep learning on freely available satellite time series lowers that floor. Annual satellite composites, cloud-screened with Cloud Score+ quality mosaics on a 90 m stand grid, feed subsequence models, a temporal convolutional network and a Transformer encoder, augmented with annual climate variables that govern spruce beetle development and survival, a warmth index built on the 17 °C univoltinism threshold, winter minimum temperature and lagged summer means, trained on dead-spruce crowns digitised from statewide sub-metre image mosaics of 2020 and 2023; comparison of the two epochs supplies interval-censored mortality-onset labels, verified pre-mortality trajectories and a cross-epoch consistency check on the labels themselves. Models are benchmarked against the pre- to post-outbreak shortwave-infrared reflectance change that defines the current floor, under block spatial cross-validation, with skill reported per severity stratum and evaluated independently against a published high-resolution severity product whose footprint no training fold touches. Detection skill in the 0.01 to 0.10 stratum, the detectability floor per method, onset-dating error and the effect of interval supervision, the contribution of climate variables to detection skill, and correspondence of the reconstructed 2016 to 2025 outbreak progression with the aerial survey record are all pending execution of the pre-registered analysis. The severity strata, metrics and decision rules were fixed by pre-registration before outcome data were analysed.

The declarative title is conditional on the primary hypothesis confirming. If it disconfirms, the title is revised before submission.

## Status

Framed, surveyed, designed and pre-registered, frozen 2026-08-11 at commit `7c73de8`, and now in the execution phase. No outcome data have been analysed and no severity value has been joined to a predictor. The confirmatory results tables render as pre-registered shells with every cell marked pending.

Built and checked: the analysis cube, the annual composites, the climate covariates, the dead-crown endmember, the synthetic pipeline validation and the evaluation harness. Under revision: the crown network, whose committed figures rest on a label set that has since changed. Blocking: label digitisation, and within it the annotation-scope decision.

Two amendments are open and unapplied, both drafted while the amendment window is still legitimate because labelling has not yet touched outcomes. The first would settle whether Sentinel-2 L1C replaces Landsat for 2016 to 2018. The second would promote a random forest after Bright et al. (2020) to the comparator for the primary hypothesis, on the grounds that a two-window reflectance difference is not the published state of the art. Neither is in force.

## Results

Every value below is computed at render time from saved code and saved inputs. Nothing here is an outcome analysis.

### Analysis cube

Forty-eight files across twelve gapless annual dates, 1 August 2014 to 1 August 2025, four bands, 2385 rows by 2023 columns matching the source composite geometry. Landsat 8 carries 2014 to 2018 and Sentinel-2 carries 2019 onward.

### Composite density

Mean clear observations per cell after Cloud Score+ masking at 0.40, which is why the pre-outbreak baseline is Landsat rather than Sentinel-2.

| Sensor | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Landsat 8 | 3.2 | 3.3 | 2.6 | 3.2 | 2.7 | | | | | | | |
| Sentinel-2 L2A | | | 1.7 | 1.8 | 1.9 | 24.2 | 19.3 | 13.0 | 13.1 | 14.4 | 9.9 | 11.6 |

Sentinel-2 Level-2A surface reflectance is effectively empty over this area before 2019 and holds nothing at all in 2015.

### Dead-crown endmember

Measured from the published crown delineations rather than assumed, under two estimators, over 3460 cells reaching a maximum severity of 0.386. The endmember is the fitted reflectance change per unit dead-crown area, so a stand at severity 0.05 moves by one twentieth of the tabulated value.

| Estimator | Band | Endmember | 95% CI | R² |
|---|---|---|---|---|
| Change | SWIR1 | +0.1378 | +0.1044 to +0.1712 | 0.019 |
| Change | SWIR2 | +0.0819 | +0.0619 to +0.1019 | 0.018 |
| Change | NIR | +0.2047 | +0.1295 to +0.2798 | 0.008 |
| Change | Red | +0.0158 | +0.0010 to +0.0306 | 0.001 |
| Level | SWIR1 | −0.0479 | −0.0986 to +0.0028 | 0.001 |

The measured SWIR1 change of +0.138 is two and a half times the 0.055 previously assumed. The level estimator returns the opposite sign at R² 0.001, because it measures between-cell confounding by stand type, slope and shadow rather than mortality; both are reported so the difference is visible. The positive NIR slope runs against crown-scale expectation and is unresolved, being either understory response to canopy opening or a Landsat to Sentinel band-pass difference.

### Synthetic validation

The mandatory pipeline test, run at both endmembers on 485 disturbed and 515 undisturbed synthetic stands. It scores seven-way severity assignment, which is not the primary hypothesis's detection task, and carries no climate channels and no interval supervision.

| Endmember | Stands recognised disturbed | Recall 0.05 to 0.1 | Recall 0.1 to 0.2 | Recall above 0.2 | Onset MAE, years | Within one year |
|---|---|---|---|---|---|---|
| Assumed 0.055 | 33 of 485 | 0.000 | 0.012 | 0.630 | 0.97 | 0.788 |
| Measured 0.138 | 103 of 485 | 0.011 | 0.163 | 0.726 | 0.71 | 0.864 |

The measured contrast trebles the stands recognised as disturbed and lifts recall between 0.1 and 0.2 more than tenfold, and onset dating improves on both measures. Everything below 0.05 stays wholly unrecovered under both endmembers. Treat this as an early warning on the primary hypothesis and on the declarative title, not as a forecast of either.

### Crown network


## Figures

Figure 1. Analysis extents in Southcentral Alaska: the Matanuska-Susitna Borough application extent, the confirmatory study window holding all training blocks and folds, and the independent severity reference footprint, over aerial survey spruce beetle damage 2016 to 2025, with rivers, highways and settlements. Drawn in UTM zone 5N with a matching projected graticule.

![Study area and outbreak extent](03.outputs/figures/fig-studyarea.png)

## Tables

Tables render live in `01.manuscript/manuscript.qmd`, in declaration order. Those marked pending carry their final structure with every cell awaiting the pre-registered analysis.

| # | Table | State |
|---|---|---|
| 1 | Input datasets, their roles and access terms | Built |
| 2 | Tuning pairs from the published crown delineations | Built |
| 3 | Fine-tuning of the four-band crown network, per epoch | Under revision |
| 4 | Choice of operating point for the triage queue | Under revision |
| 5 | Triage queue by mosaic epoch, blocks and candidates | Under revision |
| 6 | Assembled annual composites and clear-observation density | Built |
| 7 | Analysis cube as loaded, with its integrity checks | Built |
| 8 | Dead-crown endmember under two estimators | Built |
| 9 | Synthetic validation at both endmembers | Built |
| 10 | Evaluation harness checks on known inputs | Built |
| 11 | Severity estimation error per stratum and model | Pending |
| 12 | Detection skill per stratum and model | Pending |
| 13 | Test of the primary hypothesis in the 0.01 to 0.10 stratum | Pending |
| 14 | Onset-year error by model and supervision regime | Pending |
| 15 | Contribution of climate channels | Pending |
| 16 | Agreement with the independent severity reference | Pending |
| 17 | Reconstructed annual outbreak area against aerial survey | Pending |

## Reproduction

The manuscript is executable: every number and figure is computed at render time from `01.manuscript/manuscript.qmd`. Render with `quarto render manuscript.qmd --to html` from inside `01.manuscript/`. Inputs are retrieved by `05.scripts/00_download_inputs.sh` and verified by `05.scripts/01_verify_inputs.R`; all input data are open sources documented in `02.inputs/README.md`, with one declared exception, the licensed Maxar label imagery, which is processed locally and never redistributed.

R is the CRAN build at `/usr/local/bin/R`; Python is MacPorts `python3` 3.12. Large third-party data, model checkpoints and image chips are not committed. The crown-network checkpoint is regenerable from the manuscript.
