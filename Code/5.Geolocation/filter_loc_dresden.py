#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path
import pandas as pd

NER_ROOT = Path("Data/NER")

OUT_WITHIN_20KM = Path("Data/Geolocation_Metadata/combined_places_dresden_20km.csv")
OUT_NOT_GEOREF = Path("Data/Geolocation_Metadata/combined_places_not_georeferenced.csv")

# Dresden city center (Altmarkt / inner city vicinity). Adjust if you prefer another point.
DRESDEN_LAT = 51.0504
DRESDEN_LON = 13.7373
RADIUS_KM = 20.0

# Type filter (case-insensitive)
PLACE_TYPES = {"place", "loc", "location"}

# Output separator
OUT_SEP = ";"


def clean_colname(c: str) -> str:
    return str(c).replace("\ufeff", "").strip()


def read_csv_flexible(fp: Path) -> pd.DataFrame:
    # auto-detect separator; try a few encodings
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(fp, dtype=str, encoding=enc, sep=None, engine="python")
            df.columns = [clean_colname(c) for c in df.columns]
            return df
        except Exception as e:
            last_err = e
    assert last_err is not None
    raise last_err


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points (km)."""
    r = 6371.0088  # mean Earth radius (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def to_float_series(s: pd.Series) -> pd.Series:
    # handle commas as decimal separators, stray spaces, etc.
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def main() -> int:
    if not NER_ROOT.exists():
        raise FileNotFoundError(f"Missing folder: {NER_ROOT.resolve()}")

    csv_files = sorted([p for p in NER_ROOT.rglob("*.csv") if p.parent != NER_ROOT])
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found under: {NER_ROOT.resolve()}")

    within_frames: list[pd.DataFrame] = []
    not_georef_frames: list[pd.DataFrame] = []

    required_cols = {"Entity", "Type", "Link", "latitude", "longitude", "geocode_query", "geocode_status"}

    for fp in csv_files:
        df = read_csv_flexible(fp)

        missing = required_cols - set(df.columns)
        if missing:
            # Skip files that don't have the expected schema
            continue

        # Filter types first
        t = df["Type"].astype(str).str.strip().str.casefold()
        df = df[t.isin(PLACE_TYPES)].copy()
        if df.empty:
            continue

        # Add provenance columns
        df["Subfolder"] = fp.parent.name
        df["SourceFileStem"] = fp.stem

        # Convert coordinates
        lat = to_float_series(df["latitude"])
        lon = to_float_series(df["longitude"])

        has_coords = lat.notna() & lon.notna()

        # 1) Not georeferenced: missing lat/lon
        df_not = df[~has_coords].copy()
        if not df_not.empty:
            not_georef_frames.append(df_not)

        # 2) Georeferenced: compute distance and keep within 20km
        df_geo = df[has_coords].copy()
        if not df_geo.empty:
            lat_geo = lat[has_coords].to_numpy()
            lon_geo = lon[has_coords].to_numpy()

            distances = [
                haversine_km(DRESDEN_LAT, DRESDEN_LON, float(la), float(lo))
                for la, lo in zip(lat_geo, lon_geo)
            ]
            df_geo["distance_to_dresden_km"] = distances

            df_within = df_geo[df_geo["distance_to_dresden_km"] <= RADIUS_KM].copy()
            if not df_within.empty:
                within_frames.append(df_within)

    # Write outputs
    OUT_WITHIN_20KM.parent.mkdir(parents=True, exist_ok=True)

    if within_frames:
        out_within = pd.concat(within_frames, ignore_index=True).fillna("")
        out_within.to_csv(OUT_WITHIN_20KM, sep=OUT_SEP, index=False, encoding="utf-8")
        print(f"Wrote: {OUT_WITHIN_20KM} ({len(out_within)} rows)")
    else:
        print("No georeferenced Place/LOC/Location entries found within 20km of Dresden.")

    if not_georef_frames:
        out_not = pd.concat(not_georef_frames, ignore_index=True).fillna("")
        out_not.to_csv(OUT_NOT_GEOREF, sep=OUT_SEP, index=False, encoding="utf-8")
        print(f"Wrote: {OUT_NOT_GEOREF} ({len(out_not)} rows)")
    else:
        print("No non-georeferenced Place/LOC/Location entries found (missing latitude/longitude).")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise