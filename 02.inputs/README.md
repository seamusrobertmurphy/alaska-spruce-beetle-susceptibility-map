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

| `climate/` | Daymet v4 derived channel rasters, 1 km, 2012-2023: warmth index (degree-hours > 17 C, Jun-Sep), winter minimum (Nov-Mar), summer mean | GEE NASA/ORNL/DAYMET_V4, computed by manuscript chunk | Daymet: freely available (Thornton et al. 2021) | Regional series in `derived/climate_series.csv`. |
| pilot imagery | USDA NRCS `alaska_vivid_2023_30cm` ImageServer (public REST, export/download enabled, no licence text on item; 4-band 30 cm) | apps.geo.fpac.usda.gov | Public service | Chip-export route for label imagery; state Geoportal EULA route not needed for 2023 epoch. 2020 50 cm equivalent to be verified. |

## Streaming or on-demand (not downloaded)

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
