#!/usr/bin/env python3
"""Tests whether the Planetary Computer's Sentinel-1 RTC carries thermal noise.

Written 2026-09-09 for the task at 05.tasks/2026-09-09-task-thermal-noise.md.
The hypothesis under test, recorded in the project's memory note on Sentinel-1 radar,
is that the 1.46 dB VH and 0.77 dB VV residual against S1GBM is uncorrected
thermal noise, which would need the RTC product to have skipped the step the
ESA noise annotation exists for.

Three products are compared per block per channel, all from one datatake of
descending track 131 on 2021-07-21, datatake 038878_049672. The RTC assets
come from sentinel-1-rtc. The GRD digital numbers come from sentinel-1-grd
and are calibrated here twice from the product's own annotation, once without
and once with thermal noise removal. The blocks straddle two slices of the
datatake, so both slices are used and the slice is recorded per block.

The equations implemented, quoted from the source documents.

Calibration, ESA-EOPG-CSCOP-TN-0002 issue 1 rev 0, 21/05/2015, section 4,
page 7: "it is possible to calibrate the data using straight away the
calibration LUTs using the following relations" sigma0 = DN^2 / A_sigma^2,
beta0 = DN^2 / A_beta^2, gamma0 = DN^2 / A_gamma^2, "where DN is the pixel
Digital Number being in the case of: GRD: the pixel amplitude directly taken
from the measurement file". Section 3.3 maps A_gamma to
/calibration/calibrationVectorList/calibrationVector/gamma and A_sigma to
.../sigmaNought.

Noise removal, Sentinel-1 Product Specification S1-RS-MDA-52-7441 issue 3
rev 7, 27/02/2020, section 6.3.3, page 6-106: "It is also possible to obtain
calibrated data and remove the estimated noise in one step by considering the
subtraction of the noise in the formula described in 6.3.2 as follows:
value(i) = (DN_i^2 - eta_i) / A_i^2" where "eta_i = noiseLut(i)" and "A_i =
one of betaNought(i), sigmaNought(i), gamma(i), dn(i)", and "For any pixel i
that falls between points in the LUT the value is found by bilinear
interpolation."

Noise matrix, MPC-0392 DI-MPC-TN issue 1.1, 2017-11-28, section 6, page 13,
equation 1: "DN(i,j)^2_denoised = (|DN(i,j)|^2 - eta(i,j)) < 0", where "< 0"
means "clipping all negative to 0"; and section 6.1.2.3, page 17: "The full
(range and azimuth) denoising matrix is obtained by element-multiplication of
the noiseRangeMatrix_ with the noiseAzimuthMatrix_." The range vectors are
interpolated in pixel and then in line, and the azimuth vector of the swath
block holding the pixel is interpolated in line, as sections 6.1.2.1 and
6.1.2.2 describe.

Nothing is downloaded whole. The GRD and RTC measurement files are
cloud-optimised GeoTIFFs and are read by HTTP range request over each block's
window; the annotation XML is read into memory and discarded. Nothing is
written except the CSV.

    python3 05.scripts/20_thermal_noise_test.py [--flat-deg 2]

Writes 03.outputs/thermal_noise_test.csv.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.update({
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIPLEX": "YES", "GDAL_HTTP_VERSION": "2",
    "VSI_CACHE": "TRUE", "VSI_CACHE_SIZE": "33554432", "GDAL_CACHEMAX": "64",
})

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from pyproj import Transformer
from rasterio.features import geometry_mask, rasterize
from rasterio.windows import Window, from_bounds
from scipy.interpolate import LinearNDInterpolator, RectBivariateSpline
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "02.inputs" / "derived" / "sample_blocks.gpkg"
DEM = ROOT / "02.inputs" / "covariates" / "dem_3dep_200m.tif"
OUT = ROOT / "03.outputs" / "thermal_noise_test.csv"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/"
DATATAKE = "300658"
DATE = "2021-07-21"
TRACK = 131
GRD_IDS = [
    "S1A_IW_GRDH_1SDV_20210721T162913_20210721T162938_038878_049672",
    "S1A_IW_GRDH_1SDV_20210721T162938_20210721T163003_038878_049672",
]
LUT_FIELDS = ("noiseRangeVector/pixel,noiseRangeLut;"
              "noiseAzimuthVector/swath,firstRangeSample,lastRangeSample,"
              "line,noiseAzimuthLut;calibrationVector/pixel,gamma,sigmaNought")
MARGIN = 3

_tok = {}


def token(collection):
    """A SAS token per collection, renewed from its own msft:expiry field."""
    t = _tok.get(collection)
    if t and time.time() < t["e"] - 300:
        return t["v"]
    with urllib.request.urlopen(SAS + collection, timeout=60) as f:
        d = json.load(f)
    exp = d.get("msft:expiry")
    e = (dt.datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
         if exp else time.time() + 3300)
    _tok[collection] = {"v": d["token"], "e": e}
    return d["token"]


def item(collection, iid):
    with urllib.request.urlopen(f"{STAC}/collections/{collection}/items/{iid}",
                                timeout=120) as f:
        return json.load(f)


def fetch_xml(href, collection):
    with urllib.request.urlopen(f"{href}?{token(collection)}", timeout=120) as f:
        return ET.fromstring(f.read())


def floats(el):
    return np.array(el.text.split(), dtype="float64")


def parse_noise(root):
    rng = []
    for v in root.find("noiseRangeVectorList").findall("noiseRangeVector"):
        rng.append({"line": int(v.find("line").text),
                    "pixel": floats(v.find("pixel")),
                    "lut": floats(v.find("noiseRangeLut"))})
    rng.sort(key=lambda r: r["line"])
    azi = []
    for v in root.find("noiseAzimuthVectorList").findall("noiseAzimuthVector"):
        azi.append({"swath": v.find("swath").text,
                    "r0": int(v.find("firstRangeSample").text),
                    "r1": int(v.find("lastRangeSample").text),
                    "l0": int(v.find("firstAzimuthLine").text),
                    "l1": int(v.find("lastAzimuthLine").text),
                    "line": floats(v.find("line")),
                    "lut": floats(v.find("noiseAzimuthLut"))})
    return rng, azi


def parse_cal(root):
    cal = []
    for v in root.find("calibrationVectorList").findall("calibrationVector"):
        cal.append({"line": int(v.find("line").text),
                    "pixel": floats(v.find("pixel")),
                    "gamma": floats(v.find("gamma")),
                    "sigma": floats(v.find("sigmaNought"))})
    cal.sort(key=lambda r: r["line"])
    return cal


def interp_vectors(vectors, key, rows, cols):
    """Bilinear interpolation of sub-sampled range vectors to a pixel window.

    Each vector is interpolated along its own pixel grid at the window
    columns, then the vectors bracketing each window row are interpolated
    along line. Rows beyond the first or last vector take that vector.
    """
    lines = np.array([v["line"] for v in vectors], dtype="float64")
    lo = max(int(np.searchsorted(lines, rows[0], side="right")) - 1, 0)
    hi = min(int(np.searchsorted(lines, rows[-1], side="left")) + 1, len(lines))
    lo = max(lo, 0)
    sub = vectors[lo:hi]
    if len(sub) == 1:
        sub = vectors[max(lo - 1, 0):min(hi + 1, len(vectors))]
    lsub = np.array([v["line"] for v in sub], dtype="float64")
    at_cols = np.stack([np.interp(cols, v["pixel"], v[key]) for v in sub])
    out = np.empty((len(rows), len(cols)), dtype="float64")
    for j in range(len(cols)):
        out[:, j] = np.interp(rows, lsub, at_cols[:, j])
    return out


def noise_matrix(rng, azi, rows, cols):
    """eta(i, j) = noiseRangeMatrix * noiseAzimuthMatrix over a window."""
    eta_r = interp_vectors(rng, "lut", rows, cols)
    eta_a = np.full((len(rows), len(cols)), np.nan, dtype="float64")
    for blk in azi:
        m = (cols >= blk["r0"]) & (cols <= blk["r1"])
        if not m.any():
            continue
        prof = np.interp(rows, blk["line"], blk["lut"])
        eta_a[:, m] = prof[:, None]
    if np.isnan(eta_a).any():
        raise RuntimeError("window column outside every azimuth noise block")
    return eta_r * eta_a


class Geolocation:
    """Forward cubic spline on the product's GCP grid and a Newton inverse.

    GDAL's polynomial GCP transformer misplaced this scene's own GCPs by up
    to 386 columns, measured 2026-09-09, so the mapping is built here. The
    GCPs sit on a regular row by column grid, and lon and lat are each fitted
    as a bicubic spline of (row, col). The inverse starts from a linear
    interpolation of the scattered (lon, lat) to (row, col) and takes Newton
    steps on the spline until the residual is below a thousandth of a pixel.
    """

    def __init__(self, gcps):
        rows = np.array(sorted({g.row for g in gcps}))
        cols = np.array(sorted({g.col for g in gcps}))
        lon = np.full((len(rows), len(cols)), np.nan)
        lat = np.full((len(rows), len(cols)), np.nan)
        ri = {r: i for i, r in enumerate(rows)}
        ci = {c: i for i, c in enumerate(cols)}
        for g in gcps:
            lon[ri[g.row], ci[g.col]] = g.x
            lat[ri[g.row], ci[g.col]] = g.y
        if np.isnan(lon).any():
            raise RuntimeError("GCPs do not form a full grid")
        self.f_lon = RectBivariateSpline(rows, cols, lon, kx=3, ky=3)
        self.f_lat = RectBivariateSpline(rows, cols, lat, kx=3, ky=3)
        pts = np.array([(g.x, g.y) for g in gcps])
        self.guess = LinearNDInterpolator(pts, np.array([(g.row, g.col)
                                                         for g in gcps]))
        self.rmax, self.cmax = rows.max(), cols.max()

    def rowcol(self, lon, lat):
        rc = self.guess(lon, lat)
        if np.isnan(rc).any():
            return None
        r, c = float(rc[0]), float(rc[1])
        for _ in range(20):
            dlon = self.f_lon(r, c, grid=False) - lon
            dlat = self.f_lat(r, c, grid=False) - lat
            J = np.array([[self.f_lon(r, c, dx=1, grid=False),
                           self.f_lon(r, c, dy=1, grid=False)],
                          [self.f_lat(r, c, dx=1, grid=False),
                           self.f_lat(r, c, dy=1, grid=False)]], dtype="float64")
            step = np.linalg.solve(J, np.array([dlon, dlat], dtype="float64"))
            r -= step[0]
            c -= step[1]
            if np.abs(step).max() < 1e-3:
                break
        return r, c


def block_slopes(blocks):
    """Mean slope in degrees from the 200 m DEM over cells centred in each block."""
    with rasterio.open(DEM) as d:
        z = d.read(1).astype("float64")
        T = d.transform
        blocks = blocks.to_crs(d.crs)
        dzdy, dzdx = np.gradient(z, -T.e, T.a)
        slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        out = []
        for geom in blocks.geometry:
            for touched in (False, True):
                m = ~geometry_mask([geom], out_shape=z.shape, transform=T,
                                   invert=False, all_touched=touched)
                if m.any():
                    out.append(float(slope[m].mean()))
                    break
            else:
                out.append(np.nan)
    return np.array(out)


def db(x):
    return 10 * np.log10(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flat-deg", type=float, default=2.0,
                    help="blocks at or below this mean slope are called flat")
    a = ap.parse_args()

    blocks = gpd.read_file(BLOCKS)
    n = len(blocks)
    names = [f"block_{i + 1:03d}" for i in range(n)]
    slope = block_slopes(blocks)
    to_ll = Transformer.from_crs(blocks.crs, "EPSG:4326", always_xy=True)

    cols_out = {k: np.full(n, np.nan) for k in (
        "rtc_vv_db", "rtc_vh_db",
        "grd_gamma0_vv_db", "grd_gamma0_denoised_vv_db",
        "grd_gamma0_vh_db", "grd_gamma0_denoised_vh_db",
        "grd_sigma0_vv_db", "grd_sigma0_denoised_vv_db",
        "grd_sigma0_vh_db", "grd_sigma0_denoised_vh_db",
        "noise_fraction_vv", "noise_fraction_vh",
        "n_grd_pixels", "n_rtc_pixels")}
    scene = np.array([""] * n, dtype=object)
    slice_no = np.full(n, -1)
    ipf = np.array([""] * n, dtype=object)
    flag = np.array([""] * n, dtype=object)

    t0 = time.time()
    for gid in GRD_IDS:
        git = item("sentinel-1-grd", gid)
        rit = item("sentinel-1-rtc", gid + "_rtc")
        p = git["properties"]
        assert p["s1:datatake_id"] == DATATAKE and p["sat:relative_orbit"] == TRACK
        assert p["sat:orbit_state"] == "descending" and p["datetime"][:10] == DATE
        sl = int(p["s1:slice_number"])
        prod = fetch_xml(git["assets"]["schema-product-vv"]["href"], "sentinel-1-grd")
        ipf_v = prod.find(".//processingInformation/thermalNoiseCorrectionPerformed")
        flag_v = ipf_v.text if ipf_v is not None else "absent"
        ann = {}
        for pol in ("vv", "vh"):
            rng, azi = parse_noise(fetch_xml(git["assets"][f"schema-noise-{pol}"]["href"],
                                             "sentinel-1-grd"))
            cal = parse_cal(fetch_xml(git["assets"][f"schema-calibration-{pol}"]["href"],
                                      "sentinel-1-grd"))
            ann[pol] = (rng, azi, cal)
        print(f"slice {sl}: {gid}, thermalNoiseCorrectionPerformed={flag_v}, "
              f"{len(ann['vv'][0])} range and {len(ann['vv'][1])} azimuth noise "
              f"vectors, {len(ann['vv'][2])} calibration vectors", flush=True)

        with rasterio.open(f"{git['assets']['vv']['href']}?{token('sentinel-1-grd')}") as gvv, \
             rasterio.open(f"{git['assets']['vh']['href']}?{token('sentinel-1-grd')}") as gvh, \
             rasterio.open(f"{rit['assets']['vv']['href']}?{token('sentinel-1-rtc')}") as rvv, \
             rasterio.open(f"{rit['assets']['vh']['href']}?{token('sentinel-1-rtc')}") as rvh:
            software = gvv.tags().get("TIFFTAG_SOFTWARE", "")
            geo = Geolocation(gvv.gcps[0])
            H, W = gvv.shape
            assert rvv.crs == blocks.crs, (rvv.crs, blocks.crs)
            done = 0
            for i, geom in enumerate(blocks.geometry):
                if slice_no[i] >= 0:
                    continue
                xs, ys = zip(*geom.exterior.coords)
                lons, lats = to_ll.transform(xs, ys)
                rc = [geo.rowcol(lo, la) for lo, la in zip(lons, lats)]
                if any(v is None for v in rc):
                    continue
                rr = np.array([v[0] for v in rc])
                cc = np.array([v[1] for v in rc])
                r0, r1 = int(np.floor(rr.min())) - MARGIN, int(np.ceil(rr.max())) + MARGIN
                c0, c1 = int(np.floor(cc.min())) - MARGIN, int(np.ceil(cc.max())) + MARGIN
                if r0 < 0 or c0 < 0 or r1 >= H or c1 >= W:
                    continue
                win = Window(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
                rows = np.arange(r0, r1 + 1, dtype="float64")
                cols = np.arange(c0, c1 + 1, dtype="float64")
                poly = Polygon(zip(cc - c0, rr - r0))
                mask = rasterize([(poly, 1)], out_shape=(len(rows), len(cols)),
                                 fill=0, dtype="uint8").astype(bool)
                if mask.sum() < 100:
                    continue
                ok = True
                vals = {}
                for pol, src in (("vv", gvv), ("vh", gvh)):
                    dn = src.read(1, window=win).astype("float64")
                    if (dn[mask] == 0).any():
                        ok = False
                        break
                    rng, azi, cal = ann[pol]
                    I = dn ** 2
                    eta = noise_matrix(rng, azi, rows, cols)
                    I_dn = np.clip(I - eta, 0, None)
                    A_g = interp_vectors(cal, "gamma", rows, cols) ** 2
                    A_s = interp_vectors(cal, "sigma", rows, cols) ** 2
                    vals[pol] = {
                        "gamma0": (I / A_g)[mask].mean(),
                        "gamma0_dn": (I_dn / A_g)[mask].mean(),
                        "sigma0": (I / A_s)[mask].mean(),
                        "sigma0_dn": (I_dn / A_s)[mask].mean(),
                        "frac": eta[mask].mean() / I[mask].mean(),
                    }
                if not ok:
                    continue
                for pol, src in (("vv", rvv), ("vh", rvh)):
                    b = geom.bounds
                    rw = from_bounds(*b, src.transform).round_offsets().round_lengths()
                    arr = src.read(1, window=rw, boundless=True, fill_value=src.nodata)
                    m = ~geometry_mask([geom], out_shape=arr.shape,
                                       transform=src.window_transform(rw))
                    v = arr[m & (arr > 0)]
                    if v.size < 100:
                        ok = False
                        break
                    vals[pol]["rtc"] = float(v.mean())
                    vals[pol]["n_rtc"] = int(v.size)
                if not ok:
                    continue
                for pol in ("vv", "vh"):
                    v = vals[pol]
                    cols_out[f"rtc_{pol}_db"][i] = db(v["rtc"])
                    cols_out[f"grd_gamma0_{pol}_db"][i] = db(v["gamma0"])
                    cols_out[f"grd_gamma0_denoised_{pol}_db"][i] = db(v["gamma0_dn"])
                    cols_out[f"grd_sigma0_{pol}_db"][i] = db(v["sigma0"])
                    cols_out[f"grd_sigma0_denoised_{pol}_db"][i] = db(v["sigma0_dn"])
                    cols_out[f"noise_fraction_{pol}"][i] = v["frac"]
                cols_out["n_grd_pixels"][i] = int(mask.sum())
                cols_out["n_rtc_pixels"][i] = vals["vv"]["n_rtc"]
                scene[i], slice_no[i] = gid, sl
                ipf[i], flag[i] = software, flag_v
                done += 1
            print(f"  {done} blocks read from slice {sl} in {time.time() - t0:.0f}s",
                  flush=True)

    df = pd.DataFrame({"block": names, "damage": blocks["damage"].values,
                       "slope_deg": slope, "scene_id": scene, "slice": slice_no,
                       **cols_out})
    for pol in ("vv", "vh"):
        df[f"noise_step_{pol}_db"] = (df[f"grd_gamma0_{pol}_db"]
                                      - df[f"grd_gamma0_denoised_{pol}_db"])
        df[f"rtc_minus_grd_{pol}_db"] = df[f"rtc_{pol}_db"] - df[f"grd_gamma0_{pol}_db"]
        df[f"rtc_minus_grd_denoised_{pol}_db"] = (df[f"rtc_{pol}_db"]
                                                  - df[f"grd_gamma0_denoised_{pol}_db"])
    df["thermal_noise_correction_performed"] = flag
    df["ipf"] = ipf
    df["lut_fields"] = LUT_FIELDS
    df["flat"] = df["slope_deg"] <= a.flat_deg
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False, float_format="%.6g")

    got = df[df["slice"] >= 0]
    flat = got[got["flat"]]
    print(f"\nwrote {OUT.relative_to(ROOT)}: {len(got)} of {n} blocks read, "
          f"{len(flat)} flat at slope <= {a.flat_deg} deg, "
          f"slope median {got['slope_deg'].median():.2f} deg, "
          f"max {got['slope_deg'].max():.2f}")
    for pol in ("VV", "VH"):
        p = pol.lower()
        for lab, d in (("flat", flat), ("all", got)):
            s = d[f"noise_step_{p}_db"]
            print(f"{pol} noise step {lab:4s} n={len(d):3d} mean {s.mean():.3f} dB "
                  f"sd {s.std():.3f} min {s.min():.3f} max {s.max():.3f}; "
                  f"RTC minus GRD {d[f'rtc_minus_grd_{p}_db'].mean():+.3f} dB, "
                  f"RTC minus denoised GRD "
                  f"{d[f'rtc_minus_grd_denoised_{p}_db'].mean():+.3f} dB")


if __name__ == "__main__":
    sys.exit(main())
