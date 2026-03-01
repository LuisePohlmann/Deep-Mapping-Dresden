#Removes rows from the metadata CSV where the corresponding folder in images_of_pages does not exist (i.e., no images for that travelogue) and saves the filtered metadata to a new CSV (or overwrite original if desired).
from __future__ import annotations

from pathlib import Path
import pandas as pd
import sys

# Paths
METADATA_CSV = Path("Data/Raw_Metadata/travelogues_full_metadata.csv")
IMAGES_ROOT = Path("Data/images_of_pages")
METADATA_CSV_OUT = Path("Data/Raw_Metadata/travelogues_full_metadata_with_images.csv")  

SEP = "|"  # file is pipe-separated


def main() -> int:
    # Read metadata
    df = pd.read_csv(METADATA_CSV, sep=SEP, dtype=str, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]

    # Get all existing subfolder names
    existing_folders = {
        p.name for p in IMAGES_ROOT.iterdir() if p.is_dir()
    }

    print(f"Found {len(existing_folders)} subfolders in images_of_pages.")

    # Normalize Folder column (strip whitespace)
    df["Folder"] = df["Folder"].astype(str).str.strip()

    # Filter rows
    original_count = len(df)
    df_filtered = df[df["Folder"].isin(existing_folders)].copy()
    filtered_count = len(df_filtered)

    # Save result (overwrite original — change name if desired)
    df_filtered.to_csv(METADATA_CSV_OUT, sep=SEP, index=False, encoding="utf-8")

    print(f"Original rows: {original_count}")
    print(f"Remaining rows: {filtered_count}")
    print(f"Removed rows: {original_count - filtered_count}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise