# THE SPLIT LOCK. Draws the fixed, stratified block sample and fold assignment
# for the pre-registered analysis (docs/.../2026-08-11-detectability-floor.md).
# Run ONCE; the committed CSV is the lock. Requires the Macander conifer top
# cover raster at 02.inputs/covariates/conifer_topcover_2020.tif (ORNL DAAC
# doi:10.3334/ORNLDAAC/2032, Earthdata login required to fetch).
suppressMessages({library(sf); library(terra)})
set.seed(20260811)                      # fixed by pre-registration

root <- normalizePath(file.path(dirname(sub("--file=", "",
        grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
inputs <- file.path(root, "02.inputs")
con_f <- file.path(inputs, "covariates", "conifer_topcover_2020.tif")
stopifnot(file.exists(con_f))

tpl <- rast(file.path(inputs, "zwieback-severity", "merged_ref_h_c90c.tif"))
foot <- as.polygons(ext(tpl), crs = crs(tpl))
region <- ext(project(foot, "EPSG:32605")) + 50000   # the study window

## Candidate 512 m blocks on a regular grid
g <- rast(region, resolution = 512, crs = "EPSG:32605")
values(g) <- seq_len(ncell(g))
blocks <- as.polygons(g, dissolve = FALSE)

## Stratum 1: conifer top cover terciles (block mean via grid aggregation)
con <- project(rast(con_f), g, method = "average")
bc <- values(con, mat = FALSE)

## Stratum 2: survey damage history 2016-2025 (any spruce beetle polygon)
gdb <- file.path(inputs, "ids-region10", "AK_Region10_AllYears.gdb")
tmp <- tempfile(fileext = ".gpkg")
gdal_utils("vectortranslate", gdb, tmp,
           options = c("-where", "SURVEY_YEAR >= 2016 AND DCA_CODE IN (11009,80007)",
                       "DAMAGE_AREAS_FLAT_AllYears_AK_Rgn10"))
ids <- st_transform(st_read(tmp, quiet = TRUE), 32605)
dmg_any <- lengths(st_intersects(st_as_sf(blocks), ids)) > 0

## Eligibility: conifer present; keep blocks with >= 5% mean top cover
keep <- which(!is.na(bc) & bc >= 5)
bl <- st_as_sf(blocks[keep, ]); bl$conifer <- bc[keep]; bl$damage <- dmg_any[keep]
bl$stratum <- paste0("c", cut(bl$conifer, quantile(bl$conifer, c(0, 1/3, 2/3, 1)),
                              include.lowest = TRUE, labels = 1:3),
                     "_d", as.integer(bl$damage))
bl <- bl[!grepl("NA", bl$stratum), ]

## Sample 160 blocks proportionally, minimum 10 per stratum where available
n_total <- 160
tab <- table(bl$stratum)
alloc <- pmax(10, round(n_total * as.numeric(tab) / sum(tab)))
alloc <- round(alloc * n_total / sum(alloc))
names(alloc) <- names(tab)
samp <- do.call(rbind, lapply(names(tab), function(st) {
  cand <- bl[bl$stratum == st, ]
  cand[sample(nrow(cand), min(alloc[st], nrow(cand))), ]
}))

## 8 contiguous folds: the reference footprint is fold 8 in its entirety;
## remaining blocks split into 7 equal-count latitude bands (contiguous).
tbl_foot <- st_as_sf(project(foot, "EPSG:32605"))
in_tbl <- lengths(st_intersects(samp, tbl_foot)) > 0
samp$fold <- NA_integer_
samp$fold[in_tbl] <- 8L
yy <- st_coordinates(st_centroid(st_geometry(samp)))[, 2]
samp$fold[!in_tbl] <- as.integer(cut(rank(yy[!in_tbl], ties.method = "first"),
                                     7, labels = FALSE))

## Write the lock: geometries local, CSV committed
dir.create(file.path(inputs, "derived"), showWarnings = FALSE)
st_write(samp, file.path(inputs, "derived", "sample_blocks.gpkg"),
         delete_dsn = TRUE, quiet = TRUE)
xy <- st_coordinates(st_centroid(st_geometry(samp)))
write.csv(data.frame(block_id = seq_len(nrow(samp)), x = xy[, 1], y = xy[, 2],
                     conifer = round(samp$conifer, 1), damage = samp$damage,
                     stratum = samp$stratum, fold = samp$fold),
          file.path(inputs, "derived", "sample_blocks.csv"), row.names = FALSE)
print(table(samp$stratum, samp$fold))
cat("blocks:", nrow(samp), "| commit 02.inputs/derived/sample_blocks.csv to lock\n")
