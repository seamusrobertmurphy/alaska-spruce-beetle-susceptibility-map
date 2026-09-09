# Measures the Sentinel-1 noise floor on the 90 m analysis grid, which is where
# the severity labels live, rather than on the 512 m blocks where every earlier
# figure in this study was computed.
#
# Written 2026-09-09. The block figure of 0.39 dB averages a median of 2,601
# native 10 m pixels. A 90 m cell averages 81, which is 32 times fewer looks, so
# the speckle part of the noise grows by about 5.7 times and the block figure is
# the optimistic one. Whether the true 90 m floor is nearer 0.39 or nearer 2.21
# decides whether radar can carry this study, and it is measured here rather
# than interpolated between them.
#
# Run: Rscript 05.scripts/12_radar_noise_floor_90m.R

suppressPackageStartupMessages({library(terra)})

dir  <- "02.inputs/derived/s1_cube"
outf <- "03.outputs/radar_noise_floor_90m.csv"

files <- list.files(dir, pattern = "\\.tif$", full.names = TRUE)
files <- files[!startsWith(basename(files), "._")]
if (length(files) == 0) stop("no cube rasters yet")

meta <- do.call(rbind, lapply(files, function(f) {
  p <- strsplit(tools::file_path_sans_ext(basename(f)), "_")[[1]]
  data.frame(file = f, band = p[4], date = as.Date(p[5]),
             stringsAsFactors = FALSE)
}))
meta$month <- as.integer(format(meta$date, "%m"))
meta$year  <- as.integer(format(meta$date, "%Y"))

# Year to year spread of one cell in one summer month, the noise a multi-year
# change has to clear. July and August are reported separately so a single warm
# or wet month cannot stand for the season.
res <- do.call(rbind, lapply(c(7L, 8L), function(mm) {
  do.call(rbind, lapply(c("VV", "VH"), function(bb) {
    sel <- meta[meta$month == mm & meta$band == bb, ]
    sel <- sel[order(sel$year), ]
    if (nrow(sel) < 4) return(NULL)
    st <- rast(sel$file)
    db <- 10 * log10(st)
    sdr <- app(db, function(x) if (sum(!is.na(x)) >= 4) sd(x, na.rm = TRUE) else NA)
    v <- values(sdr); v <- v[is.finite(v)]
    data.frame(month = mm, band = bb, n_years = nrow(sel), n_cells = length(v),
               median_sd_db = median(v), mean_sd_db = mean(v),
               q25 = unname(quantile(v, 0.25)), q75 = unname(quantile(v, 0.75)))
  }))
}))

res$support <- "90 m cell"
write.csv(res, outf, row.names = FALSE)
print(res)
cat("\nfor comparison, the 512 m block figure is 0.39 dB in K0,",
    "\nand total canopy removal in Ruetschi et al. 2019 is 0.45 dB VV, 0.68 dB VH\n")
