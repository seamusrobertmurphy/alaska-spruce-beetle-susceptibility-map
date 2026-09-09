#!/usr/bin/env python3
"""Writes the filtered Sentinel-1 block stack as a sits local cube at 30 m.

Written 2026-09-09. Takes the multi-temporally filtered stack from
05.scripts/15_mt_speckle_filter.py, composites each calendar month by the mean
in linear power, and writes one raster per month per polarisation on the 30 m
grid that nests three by three inside the optical cube's 90 m cells, under the
naming sits reads with parse_info c("X1", "X2", "tile", "band", "date").

Only VV and VH are written. K0 and K1, the sum and difference of the two
intensities after Hechtl et al. 2025, are formed inside sits with sits_apply,
so the cube stays minimal and the Kennaugh step is visible in the manuscript
where the model is built rather than buried in a file on disk. Values stay in
linear power gamma0 for the same reason, because the sum has to be taken before
any conversion to decibels.

Sequential, one canvas at a time, because a 30 m frame is 43.4 million cells
and this is an 8 GB machine.

    python3 05.scripts/19_s1_cube_write.py
"""
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
FLT = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m_mtfiltered.npz"
TEMPLATE = ROOT / "02.inputs" / "derived" / "sits_cube" / \
    "SENTINEL-2_MSI_TBL01_B04_2014-08-01.tif"
OUTDIR = ROOT / "02.inputs" / "derived" / "s1_cube_30m"
RES, NCELL = 30, 17


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    z = np.load(FLT, allow_pickle=False)
    stack, dates = z["stack"], z["date"]          # (date, band, block, r, c)
    x0s, y1s = z["x0"], z["y1"]

    with rasterio.open(TEMPLATE) as t:
        prof = t.profile.copy()
        f = int(round(abs(t.transform.a) / RES))
        tr = rasterio.Affine(RES, 0, t.transform.c, 0, -RES, t.transform.f)
        h, w = t.height * f, t.width * f
    prof.update(transform=tr, height=h, width=w, dtype="float32", count=1,
                nodata=np.nan, compress="deflate", tiled=True,
                blockxsize=256, blockysize=256, predictor=2)

    # Where each block's 17 by 17 window sits on the frame.
    cols = np.round((x0s - tr.c) / RES).astype(int)
    rows = np.round((tr.f - y1s) / RES).astype(int)

    by_month = defaultdict(list)
    for i, d in enumerate(dates):
        by_month[str(d)[:7]].append(i)
    months = sorted(by_month)
    print(f"{len(months)} months, {stack.shape[2]} blocks, frame {h} by {w}",
          flush=True)

    written = 0
    for m in months:
        idx = by_month[m]
        for bi, band in enumerate(("VV", "VH")):
            path = OUTDIR / f"SENTINEL-1_RTC_TBL01_{band}_{m}-01.tif"
            if path.exists():
                continue
            with np.errstate(invalid="ignore"):
                comp = np.nanmean(stack[idx, bi], axis=0)   # (block, r, c)
            canvas = np.full((h, w), np.nan, dtype="float32")
            for b in range(comp.shape[0]):
                r0, c0 = rows[b], cols[b]
                canvas[r0:r0 + NCELL, c0:c0 + NCELL] = comp[b]
            with rasterio.open(path, "w", **prof) as dst:
                dst.write(canvas, 1)
                dst.update_tags(scenes=len(idx), month=m, res_m=RES,
                                track=int(z["track"]), filter="quegan2000_3x3",
                                units="gamma0 linear power")
            written += 1
            del canvas
        if len(idx) and months.index(m) % 12 == 0:
            print(f"  {m}: {len(idx)} scenes", flush=True)
    print(f"wrote {written} rasters to {OUTDIR.name}", flush=True)


if __name__ == "__main__":
    main()
