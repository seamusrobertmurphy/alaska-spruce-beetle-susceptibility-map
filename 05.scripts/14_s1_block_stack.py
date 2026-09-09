#!/usr/bin/env python3
"""Extracts the Sentinel-1 block stack at 30 m, one array per scene per block.

Written 2026-09-09 after Seamus pointed at OpenSARKit and the Sentinel-1 Toolbox
source. Three things follow from those and are built in here.

Thirty metres, not ninety. OpenSARKit's terrain correction graphs target 10 m or
30 m, and Seamus set 30 m as the floor because below it Landsat is the sensible
instrument and the comparator this study already uses. An earlier reading that
radar needed 90 m came from processing that omitted the step below.

The stack is kept whole rather than composited, because the multi-temporal
speckle filter of Quegan et al. 2000, which SNAP implements as
MultiTemporalSpeckleFilterOp, takes its noise reduction from the time dimension
rather than from spatial averaging. Compositing first would throw away what the
filter needs.

Only the blocks are stored. A full 30 m raster over the study frame is 43.4
million cells of which 46,240 carry data, so writing the frame per date is
99.9 per cent emptiness. A 3 by 3 filter window never crosses a block boundary
in any case, the blocks being 512 m apart.

    python3 05.scripts/14_s1_block_stack.py [--workers N]

Writes 02.inputs/derived/s1_block_stack_30m.npz, resumable through a per scene
cache under the same directory.
"""
import argparse
import datetime as dt
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

os.environ.update({
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIPLEX": "YES", "GDAL_HTTP_VERSION": "2",
    "VSI_CACHE": "TRUE", "VSI_CACHE_SIZE": "16777216", "GDAL_CACHEMAX": "32",
})

import numpy as np
import rasterio
import geopandas as gpd
from concurrent.futures import ThreadPoolExecutor
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
TEMPLATE = ROOT / "02.inputs" / "derived" / "sits_cube" / \
    "SENTINEL-2_MSI_TBL01_B04_2014-08-01.tif"
CACHE = ROOT / "02.inputs" / "derived" / "s1_scene_cache_30m"
OUT = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m.npz"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
BBOX = [-151.963, 61.52, -148.438, 63.467]
TRACK, RES, NCELL = 131, 30, 17

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
        _tok["e"] = (dt.datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
                     if exp else time.time() + 3300)
        return _tok["v"]


def scenes_on_track():
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
            pols = p.get("sar:polarizations") or []
            if "VV" not in pols or "VH" not in pols or "vv" not in a or "vh" not in a:
                continue
            out.append({"id": it["id"], "date": p["datetime"][:10],
                        "vv": a["vv"]["href"], "vh": a["vh"]["href"]})
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        if not nxt or not feats:
            break
        body = nxt[0].get("body") or body
        if "token" not in body:
            break
    out.sort(key=lambda r: (r["date"], r["id"]))
    return out


def block_grids():
    """A fixed 17 by 17 grid of 30 m cells per block, snapped to the 90 m grid.

    Snapping to the optical grid means three 30 m cells nest exactly inside each
    90 m cell, so the radar aggregates back onto the optical cube with no
    resampling.
    """
    with rasterio.open(TEMPLATE) as t:
        crs, T = t.crs, t.transform
    blocks = gpd.read_file(BLOCKS).to_crs(crs)
    grids = []
    for i, geom in enumerate(blocks.geometry):
        minx, miny, maxx, maxy = geom.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        x0 = T.c + round((cx - T.c) / RES) * RES - (NCELL // 2) * RES
        y1 = T.f + round((cy - T.f) / -RES) * -RES + (NCELL // 2) * RES
        grids.append({"block": f"block_{i + 1:03d}", "x0": x0, "y1": y1,
                      "bounds": (x0, y1 - NCELL * RES, x0 + NCELL * RES, y1)})
    return crs, grids


def read_one(src, g, dst_crs):
    x0, ymin, x1, ymax = g["bounds"]
    if src.crs == dst_crs:
        sw = from_bounds(x0, ymin, x1, ymax, src.transform)
        return src.read(1, window=sw, out_shape=(NCELL, NCELL),
                        resampling=Resampling.average,
                        boundless=True, fill_value=0).astype("float32")
    sx0, sy0, sx1, sy1 = transform_bounds(dst_crs, src.crs, x0, ymin, x1, ymax,
                                          densify_pts=21)
    pad = abs(src.transform.a)
    sw = from_bounds(sx0 - pad, sy0 - pad, sx1 + pad, sy1 + pad, src.transform)
    arr_src = src.read(1, window=sw, boundless=True, fill_value=0).astype("float32")
    dst = np.zeros((NCELL, NCELL), dtype="float32")
    reproject(source=arr_src, destination=dst,
              src_transform=src.window_transform(sw), src_crs=src.crs,
              dst_transform=from_origin(x0, ymax, RES, RES), dst_crs=dst_crs,
              resampling=Resampling.average, src_nodata=0, dst_nodata=0)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    dst_crs, grids = block_grids()
    scenes = scenes_on_track()
    todo = [s for s in scenes if not (CACHE / f"{s['id']}.npy").exists()]
    print(f"{len(scenes)} scenes on track {TRACK}, {len(todo)} to read, "
          f"{len(grids)} blocks of {NCELL} by {NCELL} at {RES} m", flush=True)

    done = {"n": 0, "fail": 0}
    plock = threading.Lock()

    def one(sc):
        for attempt in (1, 2):
            try:
                tk = token()
                out = np.full((2, len(grids), NCELL, NCELL), np.nan, "float32")
                for bi, (band, href) in enumerate((("VV", sc["vv"]),
                                                   ("VH", sc["vh"]))):
                    with rasterio.open(f"{href}?{tk}") as src:
                        for gi, g in enumerate(grids):
                            arr = read_one(src, g, dst_crs)
                            out[bi, gi] = np.where(arr > 0, arr, np.nan)
                np.save(CACHE / f"{sc['id']}.npy", out)
                break
            except Exception as e:
                if attempt == 1 and "403" in str(e):
                    with _lock:
                        _tok["e"] = 0.0
                    continue
                with plock:
                    done["fail"] += 1
                print(f"  skip {sc['id']}: {type(e).__name__}", flush=True)
                return
        with plock:
            done["n"] += 1
            if done["n"] % 25 == 0:
                print(f"  {done['n']}/{len(todo)}, {done['fail']} failed",
                      flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, todo))
    print(f"read in {time.time() - t0:.0f}s, {done['fail']} failed", flush=True)

    have = [s for s in scenes if (CACHE / f"{s['id']}.npy").exists()]
    stack = np.stack([np.load(CACHE / f"{s['id']}.npy") for s in have], axis=0)
    np.savez_compressed(
        OUT, stack=stack,
        scene_id=np.array([s["id"] for s in have]),
        date=np.array([s["date"] for s in have]),
        block=np.array([g["block"] for g in grids]),
        x0=np.array([g["x0"] for g in grids], "float64"),
        y1=np.array([g["y1"] for g in grids], "float64"),
        bands=np.array(["VV", "VH"]), res_m=RES, track=TRACK,
        crs=str(dst_crs))
    print(f"wrote {OUT.name}, stack {stack.shape}, "
          f"{OUT.stat().st_size / 1e6:.0f} MB", flush=True)


if __name__ == "__main__":
    main()
