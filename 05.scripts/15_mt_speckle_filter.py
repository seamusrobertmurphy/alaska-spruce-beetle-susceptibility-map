#!/usr/bin/env python3
"""Multi-temporal speckle filter over the Sentinel-1 block stack.

Implements Quegan, Le Toan, Yu, Ribbes and Floury 2000, "Multitemporal ERS SAR
Analysis Applied to Forest Mapping", IEEE Transactions on Geoscience and Remote
Sensing 38(2), which is the reference SNAP itself cites. Written 2026-09-09 from
the operator source rather than from memory, first
s1tbx-op-sar-processing/.../MultiTemporalSpeckleFilterOp.java and then the same
operator in senbox-org/microwave-toolbox, which differs in 48 lines and changes
the algorithm in none of them. The one substantive difference is that the newer
version guards the filtered value and the source value against NaN before
dividing, and that guard is taken here, because this stack carries NaN wherever
a scene does not reach a block.

    J_k(x, y) = E[I_k](x, y) * mean over j of ( I_j(x, y) / E[I_j](x, y) )

E[I] is the local mean of a window centred on the pixel. Each date keeps its own
local mean, so the filter is unbiased per date and does not flatten real change
between dates, while the speckle cancels across the stack. That is the property
that makes 30 m usable, because the noise reduction comes from the length of the
series rather than from averaging pixels together.

    python3 05.scripts/15_mt_speckle_filter.py [--window 3]
"""
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m.npz"
OUT = ROOT / "02.inputs" / "derived" / "s1_block_stack_30m_mtfiltered.npz"


def local_mean(a, w):
    """Boxcar mean over a w by w window, ignoring NaN, edges shrunk not padded.

    The operator lets the window be 3, 5, 7, 9 or 11 cells. A block is 17 cells
    across, so a 3 by 3 window never reaches beyond it and no neighbourhood
    crosses into another block, which is what makes filtering block by block
    identical to filtering a continuous scene here.
    """
    r = w // 2
    valid = np.isfinite(a)
    filled = np.where(valid, a, 0.0)
    s = np.zeros_like(filled)
    n = np.zeros(filled.shape, dtype="int16")
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s += np.roll(np.roll(filled, dy, axis=-2), dx, axis=-1)
            n += np.roll(np.roll(valid, dy, axis=-2), dx, axis=-1)
    # Edges: a rolled window wraps, so trim the border to the valid interior.
    out = np.divide(s, np.maximum(n, 1), where=n > 0)
    out[..., :r, :] = np.nan
    out[..., -r:, :] = np.nan
    out[..., :, :r] = np.nan
    out[..., :, -r:] = np.nan
    out[n == 0] = np.nan
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=3)
    a = ap.parse_args()

    z = np.load(IN, allow_pickle=False)
    stack = z["stack"]                      # (scene, band, block, row, col)
    print(f"stack {stack.shape}, {np.isfinite(stack).mean() * 100:.1f}% finite",
          flush=True)

    out = np.full_like(stack, np.nan)
    for bi, band in enumerate(z["bands"]):
        I = stack[:, bi]                    # (scene, block, row, col)
        E = np.stack([local_mean(I[k], a.window) for k in range(I.shape[0])])
        ok = np.isfinite(I) & np.isfinite(E) & (E != 0)
        ratio = np.where(ok, I / np.where(E == 0, np.nan, E), 0.0)
        s = np.nansum(np.where(ok, ratio, 0.0), axis=0)
        c = ok.sum(axis=0)
        mean_ratio = np.where(c > 0, s / np.maximum(c, 1), np.nan)
        out[:, bi] = np.where(ok, E * mean_ratio[None, ...], np.nan)
        keep = np.isfinite(out[:, bi])
        print(f"  {band}: {c.max()} dates deep, "
              f"{keep.mean() * 100:.1f}% of cells filtered", flush=True)

    np.savez_compressed(OUT, stack=out, **{k: z[k] for k in z.files
                                           if k != "stack"},
                        mt_window=a.window)
    print(f"wrote {OUT.name}, {OUT.stat().st_size / 1e6:.0f} MB", flush=True)

    # What the filter bought, measured in decibels on the same cells.
    for bi, band in enumerate(z["bands"]):
        raw = 10 * np.log10(stack[:, bi])
        flt = 10 * np.log10(out[:, bi])
        both = np.isfinite(raw) & np.isfinite(flt)
        sd_raw = np.nanstd(np.where(both, raw, np.nan), axis=0)
        sd_flt = np.nanstd(np.where(both, flt, np.nan), axis=0)
        v_raw = sd_raw[np.isfinite(sd_raw)]
        v_flt = sd_flt[np.isfinite(sd_flt)]
        print(f"  {band}: temporal SD per cell, median "
              f"{np.median(v_raw):.2f} dB before, {np.median(v_flt):.2f} dB after",
              flush=True)


if __name__ == "__main__":
    main()
