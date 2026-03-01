# Adds the coplumns from full_metadata_with_images.csv to the places_dresden.csv by matching on the source page
#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

PLACES_CSV = Path(r"Data/Geolocation_Metadata/places_corrected_combined.csv") 
META_CSV = Path(r"Data/raw_Metadata/travelogues_full_metadata_with_images.csv")
OUT_CSV = Path(r"Data/Geolocation_Metadata/places_dresden_combined_with_metadata.csv")

SEP_IN_PLACES = "|"   # places file is pipe-separated
SEP_IN_META = "|"     # change to "|" if your metadata file is also pipe-separated
SEP_OUT = "|"         # final output must be pipe-separated


def clean_colname(c: str) -> str:
    return str(c).replace("\ufeff", "").strip()


def read_csv_flexible(path: Path, sep: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.resolve()}")
    # try utf-8-sig for BOM, fallback to cp1252
    try:
        df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=sep, dtype=str, encoding="cp1252")
    df.columns = [clean_colname(c) for c in df.columns]
    return df


def main() -> int:
    df_places = read_csv_flexible(PLACES_CSV, SEP_IN_PLACES)
    df_meta = read_csv_flexible(META_CSV, SEP_IN_META)

    if "Subfolder" not in df_places.columns:
        raise KeyError("Expected column 'Subfolder' in places_dresden_with_unkown.csv")

    if "Folder" not in df_meta.columns:
        raise KeyError("Expected column 'Folder' in full_metadata_with_images.csv")

    # Normalize join keys
    df_places["Subfolder"] = df_places["Subfolder"].astype(str).str.strip()
    df_meta["Folder"] = df_meta["Folder"].astype(str).str.strip()

    # Left join keeps all place rows, duplicates in metadata are preserved (many-to-many allowed)
    merged = df_places.merge(
        df_meta,
        how="left",
        left_on="Subfolder",
        right_on="Folder",
        suffixes=("", "_meta"),
    )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_CSV, sep=SEP_OUT, index=False, encoding="utf-8")

    print(f"Wrote: {OUT_CSV} ({len(merged)} rows)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise