#!/usr/bin/env python3
"""Counts Sentinel-1 descending scenes over the study bbox in the Microsoft
Planetary Computer archive, for both the Ground Range Detected collection and
the Radiometrically Terrain Corrected one.

Written 2026-09-09 to settle whether the Planetary Computer holds less than
Earth Engine over this site, which was the reason the project built its radar
extraction in Earth Engine. It queries the STAC API rather than sits, because
sits failed on both collections with "Result must be length 1, not 0" across 37
nodes after eighteen minutes, and that failure had to be told apart from an
empty archive.
"""
import csv
import json
import urllib.request
from pathlib import Path

URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
BBOX = [-151.963, 61.52, -148.438, 63.467]  # study blocks, WGS84
OUT = Path(__file__).resolve().parents[1] / "03.outputs" / "mpc_s1_inventory.csv"


def count(collection, year, orbit):
    body = {"collections": [collection], "bbox": BBOX,
            "datetime": f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z",
            "query": {"sat:orbit_state": {"eq": orbit}}, "limit": 500}
    scenes, days = 0, set()
    while True:
        req = urllib.request.Request(
            URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as f:
            page = json.load(f)
        feats = page.get("features", [])
        scenes += len(feats)
        days.update(x["properties"]["datetime"][:10] for x in feats)
        nxt = [l for l in page.get("links", []) if l.get("rel") == "next"]
        if not nxt or not feats:
            break
        body = nxt[0].get("body") or body
        if "token" not in body:
            break
    return scenes, len(days)


def main():
    rows = []
    for collection in ("sentinel-1-grd", "sentinel-1-rtc"):
        for year in range(2017, 2027):
            scenes, days = count(collection, year, "descending")
            rows.append({"collection": collection, "year": year,
                         "orbit": "descending", "scenes": scenes,
                         "distinct_days": days})
            print(collection, year, scenes, days)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
