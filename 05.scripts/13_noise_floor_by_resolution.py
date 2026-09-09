#!/usr/bin/env python3
"""Measures the Sentinel-1 noise floor against pixel size, from 30 m to 180 m.

Written 2026-09-09. Seamus set 30 m as the floor for any cube here, because
below that Landsat is the sensible instrument and the comparator this study
already uses. The structural hypothesis, needle loss then branch fall then stem
fall, wants pixels fine enough to separate the objects that change. Radar gets
noisier as pixels shrink, because its true ground resolution is 20 by 22 m with
4.4 looks whatever the 10 m pixel spacing suggests, so a 30 m pixel holds about
1.4 independent resolution cells and a 180 m pixel about 74.

The quantity is the year-to-year standard deviation of one cell in July, in
decibels, which is the noise a multi-year change has to clear. It is measured at
each pixel size over the same blocks and the same scenes, so the only thing that
differs is how many looks average together.

    python3 05.scripts/13_noise_floor_by_resolution.py

Writes 03.outputs/radar_noise_by_resolution.csv.
"""
import csv
import json
import os
import threading
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.update({
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIPLEX": "YES", "GDAL_HTTP_VERSION": "2",
    "VSI_CACHE": "TRUE", "VSI_CACHE_SIZE": "16777216", "GDAL_CACHEMAX": "32",
})

import numpy as np
import rasterio
import geopandas as gpd
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
TEMPLATE = ROOT / "02.inputs" / "derived" / "sits_cube" / \
    "SENTINEL-2_MSI_TBL01_B04_2014-08-01.tif"
OUT = ROOT / "03.outputs" / "radar_noise_by_resolution.csv"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
BBOX = [-151.963, 61.52, -148.438, 63.467]
TRACK = 131
RESOLUTIONS = [30, 60, 90, 180]
MONTH = 7

_tok = {"v": None, "e": 0.0}
_lock = threading.Lock()


def token():
    with _lock:
        if time.time() < _tok["e"] - 300:
            return _tok["v"]
        with urllib.request.urlopen(SAS, timeout=60) as f:
            d = json.load(f)
        _tok["v"] = d["token"]
        exp = d.get("msft:expiry")
        if exp:
            import datetime as _dt
            _tok["e"] = _dt.datetime.fromisoformat(
                exp.replace("Z", "+00:00")).timestamp()
        else:
            _tok["e"] = time.time() + 3300
        return _tok["v"]


def july_scenes():
    body = {"collections": ["sentinel-1-rtc"], "bbox": BBOX,
            "datetime": "2017-06-03T00:00:00Z/2026-12-31T23:59:59Z",
            "query": {"sat:orbit_state": {"eq": "descending"},
                      "sat:relative_orbit": {"eq": TRACK}}, "limit": 500}
    out = []
    while True:
        req = urllib.request.Request(STAC, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as f:
            page = json.load(f)
        feats = page.get("features", [])
        for it in feats:
            p, a = it["properties"], it.get("assets", {})
            if int(p["datetime"][5:7]) != MONTH:
                continue
            if "VV" not in (p.get("sar:polarizations") or []):
                continue
            if "vv" not in a or "vh" not in a:
                continue
            out.append({"id": it["id"], "year": int(p["datetime"][:4]),
                        "vv": a["vv"]["href"], "vh": a["vh"]["href"]})
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        if not nxt or not feats:
            break
        body = nxt[0].get("body") or body
        if "token" not in body:
            break
    return out


def read_block(src, bounds, res, dst_crs):
    """One block at one pixel size, averaged from the native pixels."""
    x0, ymin, x1, ymax = bounds
    w = max(int(round((x1 - x0) / res)), 1)
    h = max(int(round((ymax - ymin) / res)), 1)
    dst_t = from_origin(x0, ymax, res, res)
    if src.crs == dst_crs:
        sw = from_bounds(x0, ymin, x1, ymax, src.transform)
        return src.read(1, window=sw, out_shape=(h, w),
                        resampling=Resampling.average,
                        boundless=True, fill_value=0).astype("float32")
    sx0, sy0, sx1, sy1 = transform_bounds(dst_crs, src.crs, x0, ymin, x1, ymax,
                                          densify_pts=21)
    pad = abs(src.transform.a)
    sw = from_bounds(sx0 - pad, sy0 - pad, sx1 + pad, sy1 + pad, src.transform)
    arr_src = src.read(1, window=sw, boundless=True, fill_value=0).astype("float32")
    dst = np.zeros((h, w), dtype="float32")
    reproject(source=arr_src, destination=dst,
              src_transform=src.window_transform(sw), src_crs=src.crs,
              dst_transform=dst_t, dst_crs=dst_crs,
              resampling=Resampling.average, src_nodata=0, dst_nodata=0)
    return dst


def main():
    with rasterio.open(TEMPLATE) as t:
        dst_crs = t.crs
    blocks = gpd.read_file(BLOCKS).to_crs(dst_crs)
    # A subsample of blocks keeps this to one measurement rather than a rebuild.
    bounds = [g.bounds for g in blocks.geometry][:40]

    scenes = july_scenes()
    print(f"{len(scenes)} July scenes on track {TRACK}, "
          f"{len(sorted({s['year'] for s in scenes}))} years", flush=True)

    # stack[res][band][block_index] -> list of per-year mean-per-cell arrays
    store = {r: {b: defaultdict(dict) for b in ("VV", "VH")} for r in RESOLUTIONS}
    slock = threading.Lock()

    def one(sc):
        tk = token()
        for band, href in (("VV", sc["vv"]), ("VH", sc["vh"])):
            try:
                with rasterio.open(f"{href}?{tk}") as src:
                    for bi, bd in enumerate(bounds):
                        bb = (bd[0], bd[1], bd[2], bd[3])
                        for res in RESOLUTIONS:
                            a = read_block(src, bb, res, dst_crs)
                            a = np.where(a > 0, a, np.nan)
                            if not np.isfinite(a).any():
                                continue
                            with slock:
                                store[res][band][bi].setdefault(sc["year"], []).append(a)
            except Exception as e:
                print(f"  skip {sc['id']} {band}: {type(e).__name__}", flush=True)

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(one, scenes))

    rows = []
    for res in RESOLUTIONS:
        for band in ("VV", "VH"):
            sds = []
            for bi, years in store[res][band].items():
                # one value per cell per year, averaged over that July's scenes
                per_year = {}
                for y, arrs in years.items():
                    shp = arrs[0].shape
                    ok = [a for a in arrs if a.shape == shp]
                    per_year[y] = np.nanmean(np.stack(ok), axis=0)
                if len(per_year) < 4:
                    continue
                stack = np.stack([per_year[y] for y in sorted(per_year)])
                db = 10 * np.log10(stack)
                with np.errstate(invalid="ignore"):
                    sd = np.nanstd(db, axis=0, ddof=1)
                sds.append(sd[np.isfinite(sd)].ravel())
            if not sds:
                continue
            v = np.concatenate(sds)
            cells_per_res = (512 / res) ** 2
            looks = (res / 20.0) * (res / 22.0) * 4.4
            rows.append({"resolution_m": res, "band": band,
                         "n_cells": int(v.size),
                         "median_sd_db": round(float(np.median(v)), 3),
                         "mean_sd_db": round(float(np.mean(v)), 3),
                         "q25_db": round(float(np.percentile(v, 25)), 3),
                         "q75_db": round(float(np.percentile(v, 75)), 3),
                         "equivalent_looks": round(looks, 1)})
            print(rows[-1], flush=True)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
