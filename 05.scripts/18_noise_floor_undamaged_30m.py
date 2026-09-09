#!/usr/bin/env python3
"""The honest Sentinel-1 noise floor: undamaged blocks, summer, 30 m, filtered.

Written 2026-09-09. Every earlier floor in this study was a year-to-year spread
over all 160 blocks, 96 of which the aerial survey recorded damage in, so every
one of them carried signal and was an upper bound on noise rather than a noise
floor. This one uses only the 64 blocks the survey never recorded damage in,
where nothing the study is looking for has happened, so what is left is what the
instrument and the seasons do on their own.

Two quantities, each before and after the multi-temporal filter, each in VV and
VH, June through September only.

Repeatability is the spread between scenes inside one calendar month at one
cell, in decibels. Nothing can have changed in the forest inside a month, so
this is instrument noise plus weather.

The year-to-year floor is the spread of the monthly mean at one cell across the
years, in decibels, for the same calendar month. This is what a multi-year
change has to clear, and it carries weather between years on top of noise.

    python3 05.scripts/18_noise_floor_undamaged_30m.py
"""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m.npz"
FLT = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m_mtfiltered.npz"
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
OUT = ROOT / "03.outputs" / "radar_noise_floor_undamaged_30m.csv"
MONTHS = (6, 7, 8, 9)


def db(a):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 10 * np.log10(a)


def floors(stack, dates, keep):
    """Repeatability and year-to-year floor, per band, on the kept blocks."""
    years = np.array([int(d[:4]) for d in dates])
    months = np.array([int(d[5:7]) for d in dates])
    out = {}
    for bi, band in enumerate(("VV", "VH")):
        x = db(stack[:, bi][:, keep])          # (date, block, row, col)
        rep, yr = [], []
        for m in MONTHS:
            monthly = {}
            for y in sorted(set(years)):
                sel = (years == y) & (months == m)
                if sel.sum() == 0:
                    continue
                a = x[sel]
                n = np.isfinite(a).sum(axis=0)
                if sel.sum() >= 2:
                    sd = np.nanstd(np.where(np.isfinite(a), a, np.nan), axis=0, ddof=1)
                    rep.append(sd[n >= 2])
                monthly[y] = np.nanmean(np.where(np.isfinite(a), a, np.nan), axis=0)
            if len(monthly) >= 4:
                s = np.stack([monthly[y] for y in sorted(monthly)])
                n = np.isfinite(s).sum(axis=0)
                sd = np.nanstd(s, axis=0, ddof=1)
                yr.append(sd[n >= 4])
        rep = np.concatenate(rep) if rep else np.array([])
        yr = np.concatenate(yr) if yr else np.array([])
        out[band] = (rep[np.isfinite(rep)], yr[np.isfinite(yr)])
    return out


def main():
    blocks = gpd.read_file(BLOCKS)
    undamaged = ~blocks["damage"].astype(bool).to_numpy()
    print(f"{undamaged.sum()} undamaged blocks of {len(blocks)}", flush=True)

    rows = []
    for label, path in (("unfiltered", RAW), ("mt_filtered", FLT)):
        z = np.load(path, allow_pickle=False)
        res = floors(z["stack"], z["date"], undamaged)
        for band, (rep, yr) in res.items():
            rows.append({"processing": label, "band": band,
                         "repeatability_median_db": round(float(np.median(rep)), 3),
                         "repeatability_n": int(rep.size),
                         "year_to_year_median_db": round(float(np.median(yr)), 3),
                         "year_to_year_q25_db": round(float(np.percentile(yr, 25)), 3),
                         "year_to_year_q75_db": round(float(np.percentile(yr, 75)), 3),
                         "year_to_year_n": int(yr.size),
                         "blocks": int(undamaged.sum()), "months": "6-9",
                         "support": "30 m cell"})
            print(rows[-1], flush=True)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
