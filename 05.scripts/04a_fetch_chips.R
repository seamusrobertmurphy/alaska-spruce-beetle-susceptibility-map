# Fetch label-imagery chips for every locked sample block at both mosaic
# epochs, from the public USDA NRCS Alaska Vivid image services (4-band).
# Idempotent: skips chips already on disk. Run after 03_sample_blocks.R.
suppressMessages(library(terra))
root <- normalizePath(file.path(dirname(sub("--file=", "",
        grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
blocks <- read.csv(file.path(root, "02.inputs", "derived", "sample_blocks.csv"))
svc <- c(
  "2020" = "alaska_vivid_2020_50cm",
  "2023" = "alaska_vivid_2023_30cm")
px <- c("2020" = 1024, "2023" = 1707)   # 512 m at native resolution
out_root <- file.path(root, "02.inputs", "chips")
options(timeout = 300)
for (ep in names(svc)) {
  dir.create(file.path(out_root, ep), recursive = TRUE, showWarnings = FALSE)
  for (i in seq_len(nrow(blocks))) {
    f <- file.path(out_root, ep, sprintf("block_%03d.tif", blocks$block_id[i]))
    if (file.exists(f)) next
    bb <- c(blocks$x[i] - 256, blocks$y[i] - 256,
            blocks$x[i] + 256, blocks$y[i] + 256)
    u <- sprintf(paste0(
      "https://apps.geo.fpac.usda.gov/nrcs-imagery/rest/services/",
      "ortho_imagery/%s/ImageServer/exportImage?bbox=%f,%f,%f,%f",
      "&bboxSR=32605&imageSR=32605&size=%d,%d&format=tiff&f=image"),
      svc[ep], bb[1], bb[2], bb[3], bb[4], px[ep], px[ep])
    ok <- !inherits(try(download.file(u, f, mode = "wb", quiet = TRUE),
                        silent = TRUE), "try-error")
    if (ok && inherits(try(rast(f), silent = TRUE), "try-error")) {
      unlink(f); ok <- FALSE   # HTML error body masquerading as tiff
    }
    if (!ok) message("failed: epoch ", ep, " block ", blocks$block_id[i])
    Sys.sleep(0.5)             # be polite to the public service
  }
}
n <- length(list.files(out_root, recursive = TRUE, pattern = "tif$"))
cat("chips on disk:", n, "of", 2 * nrow(blocks), "\n")
