# Measures what the Sentinel-1 K0 series can and cannot resolve, from the
# committed monthly extraction. Written 2026-09-09 to test the bound that
# Ruetschi et al. 2019 and Rignot and Way 1994 place on C-band, against this
# study's own blocks rather than against theirs.
d <- read.csv("03.outputs/s1_kennaugh_monthly.csv")
d <- d[d$K0 > 0, ]
d$db <- 10 * log10(d$K0)

# Seasonal swing across the 160 blocks, monthly means.
m <- tapply(d$db, d$month, mean)
seasonal_swing <- max(m) - min(m)

# Year-to-year repeatability inside one block in one summer month. This is the
# noise a multi-year change has to clear.
jul <- d[d$month == 7, ]
sd_yr <- tapply(jul$db, jul$block, sd)
noise_floor <- median(sd_yr, na.rm = TRUE)

# Between-block spread of the June to August mean.
s <- d[d$month %in% 6:8, ]
bm <- tapply(s$db, s$block, mean)
between_block <- sd(bm)

write.csv(
  data.frame(
    quantity = c("seasonal_swing_db", "yearly_noise_floor_db",
                 "between_block_sd_db", "windthrow_vv_db", "windthrow_vh_db"),
    value = c(seasonal_swing, noise_floor, between_block, 0.45, 0.68),
    source = c(rep("03.outputs/s1_kennaugh_monthly.csv", 3),
               rep("Ruetschi et al. 2019 Remote Sensing 11:115 p. 11", 2))),
  "03.outputs/radar_noise_floor.csv", row.names = FALSE)
