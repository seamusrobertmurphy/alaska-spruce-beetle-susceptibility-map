# Verify the sits analysis cube written by the `sits-cube-build` manuscript chunk.
# The chunk's own stopifnot runs with output suppressed, so a failure there is not
# visible in the render; this script is the check that can actually fail loudly.
# Run after any composite re-fetch or cube rebuild.
suppressMessages({library(sits); library(terra)})
root <- normalizePath(file.path(dirname(sub("--file=", "",
        grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
cube_dir <- file.path(root, "02.inputs", "derived", "sits_cube")
comp_dir <- file.path(root, "02.inputs", "composites")

cube <- sits_cube(source = "MPC", collection = "SENTINEL-2-L2A",
                  data_dir = cube_dir,
                  parse_info = c("X1", "X2", "tile", "band", "date"),
                  progress = FALSE)
tl <- sits_timeline(cube)
yrs <- as.integer(format(tl, "%Y"))
bands <- sort(sits_bands(cube))

# Every cube file must share the geometry of the composite it came from; a mismatch
# means a file survived from an earlier grid.
first <- rast(file.path(cube_dir, "SENTINEL-2_MSI_TBL01_B04_2014-08-01.tif"))
src <- rast(file.path(comp_dir, "ls_2014.tif"))

cat("files:", length(list.files(cube_dir)), "\n")
cat("dates:", length(tl), "|", format(min(tl)), "to", format(max(tl)), "\n")
cat("bands:", paste(bands, collapse = " "), "\n")
cat("tiles:", nrow(cube), "\n")
cat("dims:", paste(dim(first)[1:2], collapse = "x"), "\n")

stopifnot(
  length(list.files(cube_dir)) == 4 * length(tl),      # 4 bands per date, no strays
  identical(bands, c("B04", "B08", "B11", "B12")),
  all(diff(yrs) == 1),                                 # gapless annual timeline
  !any(yrs < 1900 | yrs > 2100),                       # catches the 22019 parse bug
  isTRUE(all.equal(as.vector(ext(first)), as.vector(ext(src)))),
  identical(dim(first)[1:2], dim(src)[1:2]))
cat("cube OK\n")
