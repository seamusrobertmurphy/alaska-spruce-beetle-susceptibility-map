#!/bin/sh
# Download open input data into 02.inputs/. Idempotent: skips files already present.
# Provenance and licences: see 02.inputs/README.md. Run from the repo root.
set -eu
IN=02.inputs

get () {
  # get <url> <dest>
  if [ -f "$2" ]; then echo "have $2"; else
    echo "fetching $2"
    curl -fL --retry 3 -o "$2" "$1"
  fi
}

# 1. Zwieback severity rasters, Zenodo 10.5281/zenodo.8423568 (record 8423569).
#    No licence declared on the record; validation use only until clarified.
mkdir -p "$IN/zwieback-severity"
for f in merged_ref_h_c30c.tif merged_ref_h_c90c.tif merged_ref_h_c250c.tif; do
  get "https://zenodo.org/records/8423569/files/$f?download=1" "$IN/zwieback-severity/$f"
done

# 2. Zwieback training/validation crown labels, Zenodo 10.5281/zenodo.10569990
#    (record 10569991), CC-BY 4.0.
mkdir -p "$IN/zwieback-labels"
get "https://zenodo.org/records/10569991/files/labels.zip?download=1" \
    "$IN/zwieback-labels/labels.zip"

# 3. Zwieback trained CNN, Zenodo 10.5281/zenodo.10569975 (record 10569976), CC-BY 4.0.
mkdir -p "$IN/zwieback-cnn"
for f in $(curl -s "https://zenodo.org/api/records/10569976" \
    | python3 -c "import json,sys; [print(x['key']) for x in json.load(sys.stdin)['files']]"); do
  get "https://zenodo.org/records/10569976/files/$f?download=1" "$IN/zwieback-cnn/$f"
done

# 4. USFS FHP Insect and Disease Survey polygons, Alaska Region 10, all years.
mkdir -p "$IN/ids-region10"
get "https://www.fs.usda.gov/foresthealth/docs/IDS_Data_for_Download/AK_Region10_AllYears.gdb.zip" \
    "$IN/ids-region10/AK_Region10_AllYears.gdb.zip"

echo "done"; du -sh "$IN"/*/
