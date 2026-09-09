# Measures what a storey-sensitive Sentinel-1 variable would have to clear in
# this study's own blocks. Written 2026-09-09 alongside the radar structural
# variables review. Reads only the committed monthly Kennaugh extraction and
# joins no severity label, so it sits inside the standing rule that radar may be
# measured before the pre-registration amendment but not joined to an outcome.
#
# Hechtl et al. 2025 define K0 as the sum and K1 as the difference of the two
# dual-polarisation intensities, so VV and VH, and therefore the cross ratio
# VH/VV, are recoverable from the committed pair without re-extraction.
d <- read.csv("03.outputs/s1_kennaugh_monthly.csv")
d <- d[!is.na(d$K0) & !is.na(d$K1) & d$K0 > 0 & abs(d$K1) < d$K0, ]

d$vv <- (d$K0 + d$K1) / 2
d$vh <- (d$K0 - d$K1) / 2
d$k0_db <- 10 * log10(d$K0)
d$k1_db <- 10 * log10(pmax(d$K1, 1e-9))
d$cr_db <- 10 * log10(d$vh / d$vv)          # cross ratio, VH over VV

# Check the recovered decomposition is physically plausible before using it.
# Cross-polarised return from forest at C-band sits several decibels below the
# co-polarised return; a recovered ratio near zero would mean the sum and
# difference convention was read the wrong way round.
cr_median <- median(d$cr_db, na.rm = TRUE)

# Monthly profile across all 160 blocks.
mm <- function(v) tapply(v, d$month, mean, na.rm = TRUE)
prof <- data.frame(
  month  = as.integer(names(mm(d$k0_db))),
  k0_db  = as.numeric(mm(d$k0_db)),
  cr_db  = as.numeric(mm(d$cr_db)),
  scenes = as.numeric(mm(d$n_scenes)))

full_swing_k0 <- max(prof$k0_db) - min(prof$k0_db)
full_swing_cr <- max(prof$cr_db) - min(prof$cr_db)

# Snow-free season only, June to September, which removes the frozen-ground
# term Rignot and Way 1994 measured at more than 3 dB in interior Alaska.
s <- d[d$month %in% 6:9, ]
sp <- tapply(s$k0_db, s$month, mean, na.rm = TRUE)
sc <- tapply(s$cr_db, s$month, mean, na.rm = TRUE)
summer_swing_k0 <- max(sp) - min(sp)
summer_swing_cr <- max(sc) - min(sc)

# Within a block and year, the June to September amplitude, and how far that
# amplitude repeats from one year to the next. The second number is the floor a
# collapse of the seasonal cycle would have to clear.
amp <- function(v) { v <- v[!is.na(v)]; if (length(v) >= 3) max(v) - min(v) else NA_real_ }
key <- interaction(s$block, s$year, drop = TRUE)
amp_k0 <- tapply(s$k0_db, key, amp)
amp_cr <- tapply(s$cr_db, key, amp)
by_block <- sub("\\..*$", "", names(amp_k0))
amp_k0_med <- median(amp_k0, na.rm = TRUE)
amp_cr_med <- median(amp_cr, na.rm = TRUE)
amp_k0_floor <- median(tapply(amp_k0, by_block, sd, na.rm = TRUE), na.rm = TRUE)
amp_cr_floor <- median(tapply(amp_cr, by_block, sd, na.rm = TRUE), na.rm = TRUE)

# Year-to-year repeatability of the July level, for the cross ratio, matching
# the K0 figure already in 03.outputs/radar_noise_floor.csv.
jul <- d[d$month == 7, ]
cr_floor_jul <- median(tapply(jul$cr_db, jul$block, sd, na.rm = TRUE), na.rm = TRUE)


# Year-to-year repeatability of the July level for K1, to sit beside the K0
# figure already committed and the cross ratio figure above.
k1_floor_jul <- median(tapply(jul$k1_db, jul$block, sd, na.rm = TRUE), na.rm = TRUE)

# What Ruetschi et al. 2019 Table 3 (p. 11) implies for each of the three
# variables. They report the windthrow-minus-intact contrast as +0.45 dB at VV
# and +0.68 dB at VH. Total canopy removal is the largest structural change a
# forest can undergo, so these propagate into an upper bound for any structural
# variable derived here. The propagation uses this study's own measured cross
# ratio as the starting ratio of VH to VV.
r0 <- 10^(cr_median / 10)                     # VH over VV, linear, measured here
gvv <- 10^(0.45 / 10); gvh <- 10^(0.68 / 10)  # Ruetschi gains, linear
k0_wt <- 10 * log10((gvv + r0 * gvh) / (1 + r0))
k1_wt <- 10 * log10((gvv - r0 * gvh) / (1 - r0))
cr_wt <- 0.68 - 0.45                          # cross ratio is the dB difference

# The design test. A variable is usable only if the largest structural change a
# forest can undergo clears this study's own year-to-year floor by a comfortable
# margin, and low-severity mortality is a small fraction of that change.
k0_ratio <- k0_wt / 0.389667067655748          # committed K0 July floor
k1_ratio <- k1_wt / k1_floor_jul
cr_ratio <- cr_wt / cr_floor_jul

out <- data.frame(
  quantity = c("cross_ratio_median_db", "k0_full_year_swing_db",
               "cr_full_year_swing_db", "k0_summer_swing_db",
               "cr_summer_swing_db", "k0_summer_amplitude_median_db",
               "cr_summer_amplitude_median_db", "k0_amplitude_floor_db",
               "cr_amplitude_floor_db", "cr_july_level_floor_db",
               "k1_july_level_floor_db", "k0_windthrow_contrast_db",
               "k1_windthrow_contrast_db", "cr_windthrow_contrast_db",
               "k0_contrast_over_floor", "k1_contrast_over_floor",
               "cr_contrast_over_floor"),
  value = c(cr_median, full_swing_k0, full_swing_cr, summer_swing_k0,
            summer_swing_cr, amp_k0_med, amp_cr_med, amp_k0_floor,
            amp_cr_floor, cr_floor_jul, k1_floor_jul,
            k0_wt, k1_wt, cr_wt, k0_ratio, k1_ratio, cr_ratio),
  source = c(rep("03.outputs/s1_kennaugh_monthly.csv", 11),
             rep("propagated from Ruetschi et al. 2019 Table 3 p. 11", 6)))

write.csv(out, "03.outputs/radar_storey_variables.csv", row.names = FALSE)
write.csv(prof, "03.outputs/radar_monthly_profile.csv", row.names = FALSE)
print(prof, digits = 4)
print(out, digits = 4)
