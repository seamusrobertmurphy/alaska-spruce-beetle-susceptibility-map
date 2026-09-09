## 07_survey_polygon_scale.R
##
## Written 2026-09-09 for the host defence and predictor variable note at
## 05.tasks/2026-09-09-host-defence-and-variables.md. It exists so that the
## scale distinction argued there, that a large regional outbreak area is many
## local attacks aggregating over years rather than one broad front, rests on
## a number computed from a committed file rather than on an impression.
##
## Input  03.outputs/survey_spread.csv, the aerial detection survey damage
##        polygons for the study region, one row per polygon, with the survey
##        year and the polygon area in acres and hectares.
## Output printed to the console and quoted in the note. Nothing is written.
##
## Run from the repository root with
##   /usr/local/bin/Rscript 05.scripts/07_survey_polygon_scale.R

f <- "03.outputs/survey_spread.csv"
d <- read.csv(f, stringsAsFactors = FALSE)

cat("file            ", f, "\n")
cat("polygons        ", nrow(d), "\n")
cat("survey years    ", min(d$year), "to", max(d$year), "\n")
cat("total hectares  ", format(round(sum(d$hectares)), big.mark = ","), "\n\n")

q <- quantile(d$hectares, c(0.5, 0.75, 0.9, 0.95, 0.99))
cat("polygon size, hectares\n")
cat("  median        ", round(q[["50%"]], 1), "\n")
cat("  75th pct      ", round(q[["75%"]], 1), "\n")
cat("  90th pct      ", round(q[["90%"]], 1), "\n")
cat("  95th pct      ", round(q[["95%"]], 1), "\n")
cat("  99th pct      ", round(q[["99%"]], 1), "\n")
cat("  maximum       ", format(round(max(d$hectares)), big.mark = ","), "\n\n")

## The share of polygons small enough to sit inside a handful of 90 m cells.
## One 90 m cell is 0.81 ha, so 8.1 ha is ten cells.
small <- sum(d$hectares <= 8.1)
cat("polygons <= 8.1 ha (ten 90 m cells)\n")
cat("  count         ", small, "\n")
cat("  share of all  ", round(100 * small / nrow(d), 1), "per cent\n")
cat("  share of area ", round(100 * sum(d$hectares[d$hectares <= 8.1]) /
                              sum(d$hectares), 1), "per cent\n\n")

## The concentration at the top of the distribution, which is the other half
## of the scale argument.
big <- sum(d$hectares > 1000)
cat("polygons > 1000 ha\n")
cat("  count         ", big, "\n")
cat("  share of area ", round(100 * sum(d$hectares[d$hectares > 1000]) /
                              sum(d$hectares), 1), "per cent\n\n")

yr <- aggregate(hectares ~ year, d, function(x) c(n = length(x), ha = sum(x)))
out <- data.frame(year = yr$year,
                  polygons = yr$hectares[, "n"],
                  hectares = round(yr$hectares[, "ha"]))
cat("polygons and hectares by survey year\n")
print(out, row.names = FALSE)
