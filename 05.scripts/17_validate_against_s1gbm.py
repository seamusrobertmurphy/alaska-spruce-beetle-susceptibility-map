#!/usr/bin/env python3
"""Checks this study's Sentinel-1 processing against an independent published one.

Written 2026-09-09. S1GBM is TU Wien's mean C-band backscatter for 2016 and 2017
at 10 m, normalised to a 38 degree incidence angle, published as
Bauer-Marschallinger et al. 2021, Scientific Data 8. It comes from a different
chain over the same ground, so if this study's block pattern does not track it,
the chain here is wrong, and finding that against a peer reviewed mosaic is
cheaper than finding it after a model is trained.

The offset between the two decomposes, and the S1GBM filenames say how. Their
statistical parameter is TMENSIG38, the temporal mean of sigma0 normalised to 38
degrees. Sigma0 is not gamma0. Gamma0 divides by the cosine of the incidence
angle, so at their fixed 38 degrees the conversion is exactly +1.03 dB and is
applied here rather than left in the residual. The extraction also reads summer
months first, so a partial run is summer weighted, and 98 per cent of the 2016 to
2017 sample falls in June through September, which this record's own monthly
means put +0.75 dB above the annual mean.

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
