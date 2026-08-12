"""Machine pre-labelling of dead spruce crowns per sample block.

Runs on the cloud GPU after 03_sample_blocks.R is locked. For each block and
mosaic epoch (2020 at 0.5 m, 2023 at 0.3 m): fetch imagery chips from the
State of Alaska Geoportal services (read the live EULA before enabling tile
access; process locally, never redistribute pixels), score dead-spruce
probability with the released network of Zwieback et al. 2024
(02.inputs/zwieback-cnn/model.p, CC-BY 4.0), refine candidate crowns with
DeepForest box prompts to SAM2 via segment-geospatial, and write vector
candidates for annotator triage.

Outputs: 02.inputs/prelabels/<epoch>/<block_id>.gpkg with fields
p_dead (mean network probability), area_m2, source_epoch.
"""
import argparse
import pathlib

BLOCKS_CSV = pathlib.Path(__file__).resolve().parents[1] / "02.inputs" / "derived" / "sample_blocks.csv"
MODEL = pathlib.Path(__file__).resolve().parents[1] / "02.inputs" / "zwieback-cnn" / "model.p"
OUT = pathlib.Path(__file__).resolve().parents[1] / "02.inputs" / "prelabels"

EPOCHS = {"2020": 0.5, "2023": 0.3}  # metres per pixel
MIN_CROWN_M2 = 1.0                   # cleaning threshold, plan section: labels
P_DEAD_KEEP = 0.3                    # candidate threshold for triage queue


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epoch", choices=EPOCHS, required=True)
    ap.add_argument("--blocks", default=str(BLOCKS_CSV))
    ap.add_argument("--device", default="cuda")
    return ap.parse_args()


def main():
    args = parse_args()
    if not pathlib.Path(args.blocks).exists():
        raise SystemExit("sample_blocks.csv missing: run and lock 03_sample_blocks.R first")
    # TODO(gpu): imagery chip fetch (Geoportal WMS, EULA-gated), torch load of
    # MODEL, tiled inference, DeepForest -> SAM2 refinement via samgeo,
    # polygonise, filter by MIN_CROWN_M2 and P_DEAD_KEEP, write per-block gpkg.
    raise SystemExit("scaffold: GPU environment not yet provisioned")


if __name__ == "__main__":
    main()
