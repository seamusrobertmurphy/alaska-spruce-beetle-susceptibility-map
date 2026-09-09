#!/usr/bin/env python3
"""Builds a Sentinel-1 local cube on the project's own 90 m grid, from
radiometrically terrain flattened gamma0, using one satellite track.

Written 2026-09-09. Three decisions are baked in and each was measured first.

The source is the Planetary Computer's sentinel-1-rtc collection rather than
Earth Engine's COPERNICUS/S1_GRD, because the Earth Engine product is sigma0
with no radiometric terrain flattening and the difference is terrain structured,
0.348 dB of block-varying offset in K0.

Only relative orbit 131 is used. Of the 160 blocks, 135 are seen by track 131
alone, 25 by both tracks and none by track 160 alone, so one track covers the
whole sample at no cost, and the 1.030 dB disagreement between the tracks never
enters the series. Track 160 is left for an independent repeatability check on
the 25 blocks that see both.

Output lands on the grid the optical cube already uses, 2385 by 2023 cells of
90 m in EPSG:32605, so the two cubes join cell for cell. Files are named for
sits' local cube reader, SENTINEL-1_RTC_TBL01_<band>_<date>.tif, five fields on
the underscore, matching parse_info c("X1", "X2", "tile", "band", "date").

Values stay in linear power gamma0. Averaging happens in power, never in
decibels, because K0 is the sum of the VV and VH intensities and the decibel of
a sum is not the sum of decibels.

    python3 05.scripts/11_s1_cube_build.py [--months N] [--workers N]

Resumable. A month whose two files already exist is skipped.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.update({
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIPLEX": "YES",
    "GDAL_HTTP_VERSION": "2",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "16777216",
    "GDAL_CACHEMAX": "32",
})

import numpy as np
import rasterio
import geopandas as gpd
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import reproject, transform_bounds

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
TEMPLATE = ROOT / "02.inputs" / "derived" / "sits_cube" / \
    "SENTINEL-2_MSI_TBL01_B04_2014-08-01.tif"
OUTDIR = ROOT / "02.inputs" / "derived" / "s1_cube"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
BBOX = [-151.963, 61.52, -148.438, 63.467]
TRACK = 131

_token = {"value": None, "expires": 0.0}
_lock = threading.Lock()


def sas_token():
    with _lock:
        if time.time() < _token["expires"] - 300:
            return _token["value"]
        with urllib.request.urlopen(SAS, timeout=60) as f:
            _token["value"] = json.load(f)["token"]
        _token["expires"] = time.time() + 3300
        return _token["value"]


def search_scenes():
    """Descending dual-polarisation RTC scenes on the chosen track."""
    body = {"collections": ["sentinel-1-rtc"], "bbox": BBOX,
            "datetime": "2017-06-03T00:00:00Z/2026-12-31T23:59:59Z",
            "query": {"sat:orbit_state": {"eq": "descending"},
                      "sat:relative_orbit": {"eq": TRACK}},
            "limit": 500}
    out = []
    while True:
        req = urllib.request.Request(
            STAC, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as f:
            page = json.load(f)
        feats = page.get("features", [])
        for it in feats:
            p, a = it["properties"], it.get("assets", {})
            pols = p.get("sar:polarizations") or []
            if "VV" not in pols or "VH" not in pols:
                continue
            if "vv" not in a or "vh" not in a:
                continue
            out.append({"id": it["id"], "date": p["datetime"][:10],
                        "vv": a["vv"]["href"], "vh": a["vh"]["href"]})
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        if not nxt or not feats:
            break
        body = nxt[0].get("body") or body
        if "token" not in body:
            break
    return out


def grid():
    """The optical cube's grid, so the two cubes join cell for cell."""
    with rasterio.open(TEMPLATE) as t:
        return t.profile.copy(), t.transform, t.crs, t.height, t.width


def block_windows(transform, height, width):
    """One window per block, snapped to whole cells of the reference grid."""
    blocks = gpd.read_file(BLOCKS).to_crs(rasterio.open(TEMPLATE).crs)
    wins = []
    for i, geom in enumerate(blocks.geometry):
        minx, miny, maxx, maxy = geom.bounds
        col0 = int(np.floor((minx - transform.c) / transform.a))
        col1 = int(np.ceil((maxx - transform.c) / transform.a))
        row0 = int(np.floor((maxy - transform.f) / transform.e))
        row1 = int(np.ceil((miny - transform.f) / transform.e))
        col0, row0 = max(col0, 0), max(row0, 0)
        col1, row1 = min(col1, width), min(row1, height)
        if col1 > col0 and row1 > row0:
            wins.append((f"block_{i + 1:03d}",
                         Window(col0, row0, col1 - col0, row1 - row0)))
    return wins


def read_scene(href, token, prof_crs, transform, height, width, wins):
    """Every block window of one scene, averaged onto the reference grid.

    Read directly rather than through a WarpedVRT. The RTC assets are already in
    EPSG:32605, the grid's own projection, so no warp is needed, and a warped
    virtual raster ignored the overviews the files carry and cost 3.45 seconds a
    window on 2026-09-09 against 0.098 seconds this way. The source origin is not
    a multiple of 90 m, so the 10 m pixels do not nest exactly in a 90 m cell and
    the averaging is left to the resampler rather than done by reshaping.
    """
    out = {}
    with rasterio.open(f"{href}?{token}") as src:
        same = src.crs == prof_crs
        for name, win in wins:
            x0 = transform.c + win.col_off * transform.a
            x1 = x0 + win.width * transform.a
            y0 = transform.f + win.row_off * transform.e
            y1 = y0 + win.height * transform.e
            ymin, ymax = min(y0, y1), max(y0, y1)
            if same:
                sw = from_bounds(x0, ymin, x1, ymax, src.transform)
                arr = src.read(1, window=sw, out_shape=(win.height, win.width),
                               resampling=Resampling.average,
                               boundless=True, fill_value=0).astype("float32")
            else:
                # The study area straddles the UTM zone 5 and 6 boundary at 150
                # west, so some scenes arrive in EPSG:32606. Read the native
                # window that covers this block in the scene's own projection,
                # with a one cell margin for the rotation, then reproject only
                # that small array. Warping the whole grid instead cost 3.45
                # seconds a window.
                sx0, sy0, sx1, sy1 = transform_bounds(
                    prof_crs, src.crs, x0, ymin, x1, ymax, densify_pts=21)
                pad = abs(src.transform.a)
                sw = from_bounds(sx0 - pad, sy0 - pad, sx1 + pad, sy1 + pad,
                                 src.transform)
                arr_src = src.read(1, window=sw, boundless=True,
                                   fill_value=0).astype("float32")
                if arr_src.size == 0:
                    continue
                arr = np.zeros((win.height, win.width), dtype="float32")
                reproject(
                    source=arr_src, destination=arr,
                    src_transform=src.window_transform(sw), src_crs=src.crs,
                    dst_transform=rasterio.windows.transform(win, transform),
                    dst_crs=prof_crs, resampling=Resampling.average,
                    src_nodata=0, dst_nodata=0)
            arr[arr <= 0] = np.nan
            if np.isfinite(arr).any():
                out[name] = arr
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    prof, transform, crs, height, width = grid()
    prof.update(dtype="float32", count=1, nodata=np.nan, compress="deflate",
                tiled=True, blockxsize=256, blockysize=256)
    wins = block_windows(transform, height, width)
    print(f"grid {height} by {width} at 90 m, {len(wins)} block windows", flush=True)

    scenes = search_scenes()
    by_month = defaultdict(list)
    for s in scenes:
        by_month[s["date"][:7]].append(s)
    months = sorted(by_month)
    print(f"{len(scenes)} scenes on track {TRACK}, {len(months)} months", flush=True)

    todo = [m for m in months
            if not all((OUTDIR / f"SENTINEL-1_RTC_TBL01_{b}_{m}-01.tif").exists()
                       for b in ("VV", "VH"))]
    print(f"{len(months) - len(todo)} months already written, {len(todo)} to do", flush=True)
    if a.months:
        todo = todo[:a.months]

    done = {"n": 0}
    wlock = threading.Lock()

    def one_month(month):
        token = sas_token()
        sums = {b: defaultdict(lambda: None) for b in ("VV", "VH")}
        counts = {b: defaultdict(lambda: None) for b in ("VV", "VH")}
        nscene = 0
        for sc in by_month[month]:
            try:
                got = {"VV": read_scene(sc["vv"], token, crs, transform,
                                        height, width, wins),
                       "VH": read_scene(sc["vh"], token, crs, transform,
                                        height, width, wins)}
            except Exception as e:
                print(f"  skip {sc['id']}: {type(e).__name__} {e}",
                      file=sys.stderr, flush=True)
                continue
            nscene += 1
            for band in ("VV", "VH"):
                for name, arr in got[band].items():
                    good = np.isfinite(arr)
                    if sums[band][name] is None:
                        sums[band][name] = np.where(good, arr, 0.0)
                        counts[band][name] = good.astype("int16")
                    else:
                        sums[band][name] += np.where(good, arr, 0.0)
                        counts[band][name] += good
        if nscene == 0:
            return
        for band in ("VV", "VH"):
            canvas = np.full((height, width), np.nan, dtype="float32")
            for name, win in wins:
                s = sums[band].get(name)
                if s is None:
                    continue
                c = counts[band][name]
                with np.errstate(invalid="ignore", divide="ignore"):
                    m = np.where(c > 0, s / np.maximum(c, 1), np.nan)
                canvas[win.row_off:win.row_off + win.height,
                       win.col_off:win.col_off + win.width] = m
            path = OUTDIR / f"SENTINEL-1_RTC_TBL01_{band}_{month}-01.tif"
            with rasterio.open(path, "w", **prof) as dst:
                dst.write(canvas, 1)
                dst.update_tags(scenes=nscene, track=TRACK, month=month)
        with wlock:
            done["n"] += 1
            print(f"  {done['n']}/{len(todo)} {month}, {nscene} scenes",
                  flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one_month, todo))
    dt = time.time() - t0
    print(f"{done['n']} months in {dt:.0f}s ({dt / max(done['n'], 1):.0f}s each)")


if __name__ == "__main__":
    main()
