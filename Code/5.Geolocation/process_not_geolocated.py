#Creates suggestions for modern spellings and tries to geolocate. If in 20km radius of Dresden, appends them to places_dresden_with_unkown.csv

#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------
# Paths (UPDATED AS REQUESTED)
# ---------------------------
IN_NOT_GEO = Path(r"Data/Geolocation_Metadata/combined_places_not_georeferenced.csv")
OUT_MODERNIZED = Path(r"Data/Geolocation_Metadata/modernised_spellings.csv")

IN_DRESDEN_20KM = Path(r"Data/Geolocation_Metadata/combined_places_dresden_20km.csv")
OUT_FINAL = Path(r"Data/Geolocation_Metadata/places_dresden_with_unkown.csv")

# CSV separators
IN_SEP = ";"
OUT_SEP = "|"

# ---------------------------
# Constants
# ---------------------------
DRESDEN_LAT = 51.0504
DRESDEN_LON = 13.7373
RADIUS_KM = 20.0

PLACE_TYPES = {"place", "loc", "location"}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CACHE_PATH = Path("Data/Geolocation_Metadata/.nominatim_cache.json")
USER_AGENT = "dresden-geocoder/1.0 (please-set-real-contact)"

# ---------------------------
# OpenAI API Setup (IDENTICAL STYLE)
# ---------------------------
load_dotenv()

api_key = os.environ.get("API_KEY")
base_url = os.environ.get("API_ENDPOINT")

client = OpenAI(api_key=api_key, base_url=base_url)
model = "openai-gpt-oss-120b"


def is_api_limit_exceeded_error(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "api limit exceeded" in msg
        or "rate limit" in msg
        or "too many requests" in msg
        or "429" in msg
        or "insufficient_quota" in msg
        or "quota" in msg
    )


def strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def run_one_place(place: str) -> str:
    prompt = (
        "Modernisiere die historische Ortsbezeichnung. "
        "Gib NUR die modernisierte Schreibweise zurück. "
        "Falls du unsicher bist, gib exakt den ursprünglichen Namen zurück.\n\n"
        f"Ort: {place}"
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    return strip_code_fences(resp.choices[0].message.content.strip())


# ---------------------------
# Geocoding helpers
# ---------------------------
def load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geocode(query: str, cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = f"q::{query}"
    if key in cache:
        return cache[key]

    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": USER_AGENT}

    time.sleep(1.0)
    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()

    data = r.json()
    result = data[0] if data else None
    cache[key] = result
    return result


def get_already_modernized() -> set:
    """Load places already modernized from OUT_MODERNIZED file."""
    if not OUT_MODERNIZED.exists():
        return set()
    try:
        df = pd.read_csv(OUT_MODERNIZED, sep=OUT_SEP, dtype=str).fillna("")
        return set(df["historical spelling"].unique()) if "historical spelling" in df.columns else set()
    except Exception:
        return set()


def get_already_geocoded() -> set:
    """Load places already geocoded from OUT_FINAL file."""
    if not OUT_FINAL.exists():
        return set()
    try:
        df = pd.read_csv(OUT_FINAL, sep=OUT_SEP, dtype=str).fillna("")
        return set(df["Entity"].unique()) if "Entity" in df.columns else set()
    except Exception:
        return set()


# ---------------------------
# MAIN
# ---------------------------
def main():
    if not IN_NOT_GEO.exists():
        raise FileNotFoundError(IN_NOT_GEO)

    df_not = pd.read_csv(IN_NOT_GEO, sep=IN_SEP, dtype=str).fillna("")
    df_dresden = pd.read_csv(IN_DRESDEN_20KM, sep=IN_SEP, dtype=str).fillna("")

    if "historical spelling" not in df_dresden.columns:
        df_dresden["historical spelling"] = ""

    # Ensure original 'Entity' is preserved under the requested name
    if "Entity" in df_not.columns:
        df_not.rename(columns={"Entity": "historical spelling"}, inplace=True)

    # Step 1 — Modernize spellings (save each result immediately and show progress)
    modernized = []
    total_not = len(df_not)
    first_mod_write = not OUT_MODERNIZED.exists()
    
    # Load already-modernized places to resume from where we left off
    already_modernized = get_already_modernized()
    print(f"ℹ️  Found {len(already_modernized)} already modernized places; resuming from {total_not - len(already_modernized)} remaining")

    for i, (_, row) in enumerate(df_not.iterrows()):
        place = row["historical spelling"]
        
        # Skip if already modernized
        if place in already_modernized:
            modernized.append("")  # placeholder for already-processed
            print(f"Skipped {i+1}/{total_not} (already modernized): '{place}'")
            continue
        
        attempt = 0
        while True:
            try:
                suggestion = run_one_place(place)
                break
            except Exception as e:
                if is_api_limit_exceeded_error(e):
                    if attempt == 0:
                        print("⚠️ Rate limit hit — waiting 60 minutes...")
                        time.sleep(60 * 60)
                        attempt += 1
                        continue
                    else:
                        raise
                else:
                    print(f"❌ Failed for {place}: {e}")
                    suggestion = ""
                    break

        modernized.append(suggestion)

        # Enforce minute-level throttling to avoid exceeding 9 requests per minute
        time.sleep(7)

        # Write the single-row result immediately to OUT_MODERNIZED
        row_out = row.copy()
        row_out["modernized_spellings"] = suggestion
        pd.DataFrame([row_out]).to_csv(OUT_MODERNIZED, sep=OUT_SEP, index=False, header=first_mod_write, mode="a", encoding="utf-8")
        first_mod_write = False

        # Progress output for modernization
        print(f"Modernized {i+1}/{total_not}: '{place}' -> '{suggestion}'")

    df_not["modernized_spellings"] = modernized
    print(f"✅ Modernization complete and written incrementally to {OUT_MODERNIZED}")

    # Step 2 — Geocode (append new rows immediately and show updated count)
    cache = load_cache()

    # Ensure OUT_FINAL starts with the existing Dresden dataset and has Certainty column
    if not OUT_FINAL.exists():
        if "Certainty" not in df_dresden.columns:
            df_dresden["Certainty"] = "uncertain"
        df_dresden.to_csv(OUT_FINAL, sep=OUT_SEP, index=False, encoding="utf-8")
        print(f"Initialized {OUT_FINAL} with {len(df_dresden)} existing rows")
    else:
        # If file exists, make sure it contains Certainty column for consistency
        try:
            existing = pd.read_csv(OUT_FINAL, sep=OUT_SEP, dtype=str).fillna("")
            if "Certainty" not in existing.columns:
                existing["Certainty"] = "uncertain"
                existing.to_csv(OUT_FINAL, sep=OUT_SEP, index=False, encoding="utf-8")
                print(f"Patched existing {OUT_FINAL} with Certainty column")
        except Exception:
            # If reading fails, continue and append — user can inspect file manually
            pass

    updated_count = 0
    total_geo = len(df_not)
    
    # Load already-geocoded places to resume from where we left off
    already_geocoded = get_already_geocoded()
    print(f"ℹ️  Found {len(already_geocoded)} already geocoded places; resuming geocoding for remaining {total_geo - len(already_geocoded)} rows")

    for i, (_, row) in enumerate(df_not.iterrows()):
        modern = row["modernized_spellings"].strip()
        historical = row["historical spelling"].strip()
        if not modern:
            print(f"Skipping {i+1}/{total_geo} (no modernized spelling)")
            continue
        
        # Skip if already geocoded
        if modern in already_geocoded:
            print(f"Skipped {i+1}/{total_geo} (already geocoded): '{modern}'")
            continue

        try:
            result = geocode(modern, cache)
        except Exception as e:
            print(f"Geocode error for '{modern}' at {i+1}/{total_geo}: {e}")
            save_cache(cache)
            continue

        if not result:
            print(f"No geocode result for '{modern}' ({i+1}/{total_geo})")
            save_cache(cache)
            continue

        lat = float(result["lat"])
        lon = float(result["lon"])

        dist = haversine_km(DRESDEN_LAT, DRESDEN_LON, lat, lon)
        if dist > RADIUS_KM:
            print(f"Outside radius for '{modern}' ({dist:.1f} km) — skipping")
            save_cache(cache)
            continue

        # Build a consistent output row dict with required columns
        out_row = row.copy()
        out_row["Entity"] = modern
        out_row["latitude"] = lat
        out_row["longitude"] = lon
        out_row["geocode_query"] = modern
        out_row["geocode_status"] = "ok_modernized"
        out_row["historical spelling"] = historical
        out_row["Certainty"] = "uncertain"

        # Append immediately to OUT_FINAL
        pd.DataFrame([out_row]).to_csv(OUT_FINAL, sep=OUT_SEP, index=False, header=False, mode="a", encoding="utf-8")
        updated_count += 1

        # Progress output for geocoding updates
        print(f"Updated lines: {updated_count} (latest: '{modern}')")

        # Persist cache after each processed line
        save_cache(cache)

    print(f"🎉 Geocoding complete — {updated_count} new rows appended to {OUT_FINAL}")


if __name__ == "__main__":
    main()