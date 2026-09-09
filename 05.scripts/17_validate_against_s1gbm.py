#!/usr/bin/env python3
"""Checks this study's Sentinel-1 processing against an independent published one.

Written 2026-09-09. S1GBM is TU Wien's mean C-band backscatter for 2016 and 2017
at 10 m, normalised to a 38 degree incidence angle, published as
Bauer-Marschallinger et al. 2021, Scientific Data 8. It comes from a different
chain over the same ground, so if this study's block pattern does not track it,
the chain here is wrong, and finding that against a peer reviewed mosaic is
cheaper than finding it after a model is trained.

Two differences are expected and neither is a fault. S1GBM is normalised to a
fixed incidence angle where this study keeps gamma0 at the observed angle, and
gamma0 divides by the cosine of that angle, which raises it. And the extraction
here reads summer months first, so a partial run is summer weighted against a
mosaic that averages the whole year, and this record's own seasonal swing is
2.16 dB with July highest.

    python3 05.scripts/17_validate_against_s1gbm.py
"""
import csv
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "03.outputs" / "s1gbm_blocks.csv"
OURS = ROOT / "03.outputs" / "s1_rtc_scene_means.csv"
OUT = ROOT / "03.outputs" / "s1gbm_validation.csv"


def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else float("nan")


def main():
    ref = {r["block"]: (float(r["s1gbm_vv_db"]), float(r["s1gbm_vh_db"]))
           for r in csv.DictReader(REF.open())}
    acc = defaultdict(lambda: {"vv": [], "vh": []})
    for r in csv.DictReader(OURS.open()):
        if r["date"][:4] not in ("2016", "2017"):
            continue
        acc[r["block"]]["vv"].append(float(r["vv"]))
        acc[r["block"]]["vh"].append(float(r["vh"]))

    rows = []
    for band, key, idx in (("VV", "vv", 0), ("VH", "vh", 1)):
        o, t = [], []
        for b, v in acc.items():
            if b in ref and len(v[key]) >= 3:
                o.append(10 * math.log10(st.mean(v[key])))
                t.append(ref[b][idx])
        rows.append({"band": band, "n_blocks": len(o),
                     "ours_median_db": round(st.median(o), 2),
                     "s1gbm_median_db": round(st.median(t), 2),
                     "offset_db": round(st.median(o) - st.median(t), 2),
                     "pearson_r": round(pearson(o, t), 3),
                     "source": "S1GBM, Bauer-Marschallinger et al. 2021 "
                               "Scientific Data 8"})
        print(rows[-1])

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
