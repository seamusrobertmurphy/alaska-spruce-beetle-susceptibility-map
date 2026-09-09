#!/usr/bin/env python3
"""Rebuilds the Sentinel-1 block series from radiometrically terrain flattened
gamma0, keeping the two descending tracks apart.

Written 2026-09-09 to replace 03.outputs/s1_kennaugh_monthly.csv, which was
taken from Earth Engine's COPERNICUS/S1_GRD. That collection is sigma0 without
radiometric terrain flattening, and on the same acquisition flattened gamma0 ran
1.030 dB above it in VV and 1.312 dB in VH, of which 0.348 dB in K0 varies block
by block and follows the terrain. The old extraction also pooled relative orbits
131 and 160, which disagree by 1.030 dB in K0 over the 25 blocks both cover,
twice the published windthrow signal, so track is carried as a column here and
never averaged across.

Values are gamma0 in linear power, not decibels, because K0 is the sum of the VV
and VH intensities and K1 their difference, after Hechtl et al. 2025 equations 1
and 2, and a sum of decibels is not the decibel of a sum.

    python3 05.scripts/10_s1_rtc_extract.py [--limit N] [--workers N]

Resumable. Each finished scene is appended to the partial file, and a rerun
skips every scene id already in it.
"""
import argparse
import csv
import json
import os
import sys
import threading
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
PARTIAL = ROOT / "03.outputs" / "s1_rtc_scene_means.csv"
OUT = ROOT / "03.outputs" / "s1_rtc_monthly.csv"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
BBOX = [-151.963, 61.52, -148.438, 63.467]
FIELDS = ["scene_id", "date", "track", "block", "vv", "vh", "n_pixels"]

_token = {"value": None, "expires": 0.0}
_lock = threading.Lock()


def sas_token():
    """MPC blob URLs need a shared access signature, and it expires hourly."""
    with _lock:
        if time.time() < _token["expires"] - 300:
            return _token["value"]
        with urllib.request.urlopen(SAS, timeout=60) as f:
            d = json.load(f)
        _token["value"] = d["token"]
        _token["expires"] = time.time() + 3300
        return _token["value"]


def search_scenes():
    """Every descending dual-polarisation RTC scene over the blocks."""
    body = {
        "collections": ["sentinel-1-rtc"],
        "bbox": BBOX,
        "datetime": "2017-01-01T00:00:00Z/2026-12-31T23:59:59Z",
        "query": {"sat:orbit_state": {"eq": "descending"}},
        "limit": 500,
    }
    out = []
    while True:
        req = urllib.request.Request(
            STAC, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as f:
            page = json.load(f)
        feats = page.get("features", [])
        for it in feats:
            p = it["properties"]
            pols = p.get("sar:polarizations") or []
            if "VV" not in pols or "VH" not in pols:
                continue
            assets = it.get("assets", {})
            if "vv" not in assets or "vh" not in assets:
                continue
            out.append({
                "id": it["id"],
                "date": p["datetime"][:10],
                "track": p.get("sat:relative_orbit"),
                "vv": assets["vv"]["href"],
                "vh": assets["vh"]["href"],
            })
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        if not nxt or not feats:
            break
        body = nxt[0].get("body") or body
        if "token" not in body:
            break
    # Summer first, then the rest in date order. The analysis is restricted to
    # the unfrozen months, because four fifths of the 2.16 dB annual swing in
    # this record is the ground freezing, so a run stopped early should leave
    # complete summers rather than complete early years.
    out.sort(key=lambda r: (int(r["date"][5:7]) not in (6, 7, 8, 9),
                            r["date"], r["id"]))
    return out


# Remote COG reads dominate the cost, so GDAL is told not to list the container
# on open, to reuse connections, and to keep a block cache. Untuned, a scene took
# 26 seconds. Do not add CPL_VSIL_CURL_ALLOWED_EXTENSIONS here: the RTC assets end
# in .rtc.tiff, and setting it to .tif failed every open on 2026-09-09.
os.environ.update({
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIPLEX": "YES",
    "GDAL_HTTP_VERSION": "2",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "16777216",
    "GDAL_CACHEMAX": "32",
    "GDAL_NUM_THREADS": "1",
})


def block_means(href, blocks_wgs, token):
    """Mean linear-power gamma0 inside each block, read window by window."""
    url = f"{href}?{token}"
    res = {}
    with rasterio.open(url) as src:
        bounds = src.bounds
        geoms = blocks_wgs.to_crs(src.crs)
        for bid, geom in zip(geoms["block"], geoms.geometry):
            minx, miny, maxx, maxy = geom.bounds
            if maxx < bounds.left or minx > bounds.right:
                continue
            if maxy < bounds.bottom or miny > bounds.top:
                continue
            win = from_bounds(minx, miny, maxx, maxy, src.transform)
            arr = src.read(1, window=win, boundless=True, fill_value=np.nan)
            arr = arr.astype("float64")
            arr[arr <= 0] = np.nan
            good = np.isfinite(arr)
            if good.sum() == 0:
                continue
            res[bid] = (float(np.nanmean(arr)), int(good.sum()))
    return res


def done_scenes():
    if not PARTIAL.exists():
        return set()
    with PARTIAL.open() as f:
        return {r["scene_id"] for r in csv.DictReader(f)}


def run(scenes, workers):
    blocks = gpd.read_file(BLOCKS)
    blocks["block"] = [f"block_{i + 1:03d}" for i in range(len(blocks))]
    blocks_wgs = blocks[["block", "geometry"]]

    if not PARTIAL.exists():
        with PARTIAL.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()

    write_lock = threading.Lock()
    counter = {"n": 0, "fail": 0}
    total = len(scenes)

    def one(sc):
        try:
            token = sas_token()
            vv = block_means(sc["vv"], blocks_wgs, token)
            vh = block_means(sc["vh"], blocks_wgs, token)
        except Exception as e:
            with write_lock:
                counter["fail"] += 1
                print(f"  fail {sc['id']}: {type(e).__name__} {e}",
                      file=sys.stderr, flush=True)
            return
        rows = []
        for bid in vv.keys() & vh.keys():
            rows.append({"scene_id": sc["id"], "date": sc["date"],
                         "track": sc["track"], "block": bid,
                         "vv": vv[bid][0], "vh": vh[bid][0],
                         "n_pixels": min(vv[bid][1], vh[bid][1])})
        with write_lock:
            with PARTIAL.open("a", newline="") as f:
                csv.DictWriter(f, fieldnames=FIELDS).writerows(rows)
            counter["n"] += 1
            if counter["n"] % 25 == 0:
                print(f"  {counter['n']}/{total} scenes, "
                      f"{counter['fail']} failed", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, scenes))
    return counter


def aggregate():
    """Monthly mean per block per track, then the Kennaugh pair."""
    acc = defaultdict(lambda: {"vv": [], "vh": [], "scenes": set()})
    with PARTIAL.open() as f:
        for r in csv.DictReader(f):
            key = (r["block"], r["date"][:4], r["date"][5:7], r["track"])
            acc[key]["vv"].append(float(r["vv"]))
            acc[key]["vh"].append(float(r["vh"]))
            acc[key]["scenes"].add(r["scene_id"])
    rows = []
    for (block, year, month, track), v in sorted(acc.items()):
        vv = float(np.mean(v["vv"]))
        vh = float(np.mean(v["vh"]))
        rows.append({"block": block, "year": int(year), "month": int(month),
                     "track": track, "VV": vv, "VH": vh,
                     "K0": vv + vh, "K1": vv - vh,
                     "n_scenes": len(v["scenes"])})
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--aggregate-only", action="store_true")
    a = ap.parse_args()

    if not a.aggregate_only:
        scenes = search_scenes()
        print(f"{len(scenes)} descending dual-pol RTC scenes found")
        already = done_scenes()
        scenes = [s for s in scenes if s["id"] not in already]
        print(f"{len(already)} already done, {len(scenes)} to do")
        if a.limit:
            scenes = scenes[:a.limit]
            print(f"limited to {len(scenes)}")
        if scenes:
            t0 = time.time()
            c = run(scenes, a.workers)
            dt = time.time() - t0
            print(f"{c['n']} scenes in {dt:.0f}s "
                  f"({dt / max(c['n'], 1):.1f}s each), {c['fail']} failed")

    if PARTIAL.exists():
        rows = aggregate()
        print(f"wrote {OUT.name}, {len(rows)} block-month-track rows")


if __name__ == "__main__":
    main()
