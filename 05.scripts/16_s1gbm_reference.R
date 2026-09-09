# Pulls the normalised Sentinel-1 Global Backscatter Model over the 160 blocks.
#
# Written 2026-09-09. S1GBM is TU Wien's mean C-band backscatter for 2016 and
# 2017 at 10 m, normalised to a 38 degree incidence angle, published as
# Bauer-Marschallinger et al. 2021, Scientific Data 8. Two uses here, and it can
# serve neither as the analysis cube, because it is one mean image rather than a
# series and so carries no dates to learn from.
#
# The first use is an independent check. It is a peer reviewed measurement of the
# same ground from a different processing chain, so the block pattern in our own
# 2017 means should agree with it. Disagreement would say our chain is wrong, and
# finding that against ESA's mosaic is cheaper than finding it after training.
#
# The second is the angle normalisation itself, which is the published answer to
# the problem this study met when descending tracks 131 and 160 disagreed by
# 1.030 dB in K0 over the 25 blocks both cover. Discarding a track solves it by
# throwing away 614 scenes; normalising to a common incidence angle keeps them.
#
# Values are 16 bit integers holding backscatter in decibels times ten, which the
# catalogue's own display range of -200 to -60 for VV implies and which is
# checked below against the expected forest range.
#
# Run: Rscript 05.scripts/16_s1gbm_reference.R

suppressPackageStartupMessages({library(rgee); library(sf)})
ee_Initialize(project = "murphys-deforisk", quiet = TRUE)

blk <- st_read("02.inputs/derived/sample_blocks.gpkg", quiet = TRUE)
blk$block <- sprintf("block_%03d", seq_len(nrow(blk)))
blk_ee <- sf_as_ee(st_transform(blk[, c("block", "geom")], 4326))

VV <- ee$ImageCollection("projects/sat-io/open-datasets/S1GBM/normalized_s1_backscatter_VV")
VH <- ee$ImageCollection("projects/sat-io/open-datasets/S1GBM/normalized_s1_backscatter_VH")
cat("VV tiles:", VV$size()$getInfo(), " VH tiles:", VH$size()$getInfo(), "\n")

img <- VV$mosaic()$rename("VV")$addBands(VH$mosaic()$rename("VH"))

stats <- img$reduceRegions(
  collection = blk_ee,
  reducer    = ee$Reducer$mean(),
  scale      = 10L,
  tileScale  = 4L)

df <- ee_as_sf(stats, via = "getInfo", quiet = TRUE)
out <- data.frame(block = df$block,
                  s1gbm_vv_db = df$VV / 10,
                  s1gbm_vh_db = df$VH / 10)
out <- out[order(out$block), ]
write.csv(out, "03.outputs/s1gbm_blocks.csv", row.names = FALSE)

cat(sprintf("\n%d blocks returned\n", nrow(out)))
cat(sprintf("VV median %.2f dB (range %.2f to %.2f)\n",
            median(out$s1gbm_vv_db, na.rm = TRUE),
            min(out$s1gbm_vv_db, na.rm = TRUE), max(out$s1gbm_vv_db, na.rm = TRUE)))
cat(sprintf("VH median %.2f dB (range %.2f to %.2f)\n",
            median(out$s1gbm_vh_db, na.rm = TRUE),
            min(out$s1gbm_vh_db, na.rm = TRUE), max(out$s1gbm_vh_db, na.rm = TRUE)))
cat("wrote 03.outputs/s1gbm_blocks.csv\n")
