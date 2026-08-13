# Input data manifest

Retrieved 2026-08-10 by `05.scripts/00_download_inputs.sh`; integrity in `SHA256SUMS.txt`.
Raw data are gitignored; this manifest and the script are the reproducible record.
No outcome analysis has been run on any of these files (pre-registration gate open).

## Downloaded

| Folder | Dataset | Source | Licence | Notes |
|---|---|---|---|---|
| `zwieback-severity/` | Spruce beetle outbreak severity, Southcentral AK 2021, GeoTIFF at 30/90/250 m | Zenodo 10.5281/zenodo.8423568 (record 8423569), Zwieback (UAF) | **None declared** (verified via Zenodo API 2026-08-10) | Validation use only until licence clarified with author; email deferred until the work is prepared (decision 2026-08-10). Companion to Zwieback et al. 2024, ISPRS J. 212:412-421. |
| `zwieback-labels/` | Hand-delineated dead-spruce crown labels, TBL area (GeoPackage per area: `_extent.gpkg`, `_labels.gpkg`) | Zenodo 10.5281/zenodo.10569990 (record 10569991) | CC-BY 4.0 | Drawn on proprietary Maxar imagery not included; reusable with attribution. |
| `zwieback-cnn/` | Trained DeepLabV3/ResNet50 PyTorch model (`model.p`) | Zenodo 10.5281/zenodo.10569975 (record 10569976) | CC-BY 4.0 | Candidate pre-labeler for our own crown digitization on Geoportal mosaics. |
| `ids-region10/` | USFS FHP Insect and Disease Survey damage polygons, Alaska Region 10, all years (file gdb, 72 files) | https://www.fs.usda.gov/foresthealth/docs/IDS_Data_for_Download/AK_Region10_AllYears.gdb.zip (last modified 2026-04-22) | US Government work, public domain | Sketch-map polygons; positional accuracy coarse; intensity is faded-trees-per-treed-area, not commensurable with pixel-fraction severity (Zwieback 2024, p. 415). Includes flown-area footprints; use them to separate absence from non-survey. |
| `covariates/` | ABoVE modeled top cover by plant functional type, Alaska and Yukon 1985-2020, v1.1; conifer top cover 2020 slice held as `conifer_topcover_2020.tif` | ORNL DAAC doi:10.3334/ORNLDAAC/2032 (Macander and Nelson 2022), Earthdata login required; retrieved 2026-08-12 | No licence string on the dataset page as read 2026-08-12; NASA DAAC distribution, cite Macander et al. 2022 (doi:10.1088/1748-9326/ac6965) | Stratifies the block sample: conifer terciles crossed with damage presence. Used by `05.scripts/03_sample_blocks.R`. |
| `climate/` | Daymet v4 derived channel rasters, 1 km, 2012-2023: warmth index (degree-hours > 17 C, Jun-Sep), winter minimum (Nov-Mar), summer mean | GEE NASA/ORNL/DAYMET_V4, computed by manuscript chunk | Daymet: freely available (Thornton et al. 2021) | Regional series in `derived/climate_series.csv`. |
| `chips/` | Label imagery chips, 512 m per sample block at both epochs, 4-band: `alaska_vivid_2020_50cm` (1024 px) and `alaska_vivid_2023_30cm` (1707 px) | USDA NRCS ImageServer REST export, apps.geo.fpac.usda.gov; fetched 2026-08-12 by `05.scripts/04a_fetch_chips.R` | Public service, export and download enabled, no licence text on either item | 320 chips, both epochs complete over the 160 locked blocks. Chip export makes the state Geoportal EULA route unnecessary for both epochs. |

## Derived

- **`composites/`**: annual Sentinel-2 (2016-2025, Cloud Score+ at 0.40) and Landsat 8
  (2014-2018, QA_PIXEL) composites on the 90 m reference grid extended 50 km, built by
  the manuscript's composite chunks. Regenerable, gitignored.
- **`derived/sits_cube/`**: the same composites split into single-band files under sits
  local-cube naming, built and validated by the `sits-cube-build` manuscript chunk.
  Regenerable from `composites/`, gitignored.

## Streaming or on-demand

- **State of Alaska Geoportal Maxar mosaics**: statewide 2020 50 cm and 2023 30 cm,
  WMS/WMTS via https://gis.data.alaska.gov/pages/imagery (DGGS records 30687, 30688).
  University/non-commercial streaming; no pixel download or redistribution. Read the
  live EULA before any tile scraping. Label source for our own crown delineations.
- **Sentinel-2 and Landsat**: via Google Earth Engine at the analysis stage; heavy
  computation runs server-side or on cloud GPU, not on the 8 GB local machine.
  Predictor data; annual composites cached under `composites/`.
- **IFSAR 5 m DEM**: https://elevation.alaska.gov/ , public domain, fetch when the
  analysis design fixes the AOI.
- **ArcticDEM 2 m strips** (CC-BY 4.0, GEE `UMN/PGC/ArcticDEM`): optional structural
  covariate; Alaska strips end mid-2022.
