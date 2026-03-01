from __future__ import annotations

from openai import OpenAI
from dotenv import load_dotenv
import os
import csv
import time
import re
import math
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests

# ----------------------------
# Load environment variables (LLM)
# ----------------------------
load_dotenv()
api_key = os.environ.get("API_KEY")
base_url = os.environ.get("API_ENDPOINT")

if not api_key or not base_url:
    raise RuntimeError("Missing API_KEY or API_ENDPOINT in your environment / .env file.")

client = OpenAI(api_key=api_key, base_url=base_url)
model = "openai-gpt-oss-120b"

# ----------------------------
# Files
# ----------------------------
INFILE = Path("places_not_geolocated.csv")
OUT_QGIS = Path("data_for_qgis_v1.csv")
OUT_SUGGESTIONS = Path("API_unknown_places.csv")  # optional audit output

# ----------------------------
# Place filtering / distance
# ----------------------------
PLACE_TYPES = {"place", "loc", "location"}
DRESDEN_LAT = 51.0504
DRESDEN_LON = 13.7373
RADIUS_KM = 20.0

# ----------------------------
# Nominatim geocoding (local check + lat/lon)
# ----------------------------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ner-geocode/1.0 (please set your email)"  # <-- CHANGE THIS
CACHE_PATH = Path(".nominatim_cache.json")
RATE_LIMIT_SECONDS = 1.1

# ----------------------------
# LLM tuning knobs
# ----------------------------
BATCH_SIZE = 50
SLEEP_BETWEEN_CALLS = 0.5
MAX_RETRIES = 2


# ----------------------------
# Helpers
# ----------------------------
def clean_colname(c: str) -> str:
    return str(c).replace("\ufeff", "").strip()


def is_missing_value(x) -> bool:
    if pd.isna(x):
        return True
    s = str(x).strip()
    return s == "" or s.lower() in {"nan", "none", "null", "n/a", "na", "-"}


def normalize_type(t: object) -> str:
    return str(t).strip().lower()


def safe_float(x: object) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
        return None
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


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


# ----------------------------
# Read + filter input rows (places only)
# ----------------------------
def read_places_not_geolocated(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = [clean_colname(c) for c in df.columns]

    if "Type" not in df.columns or "Entity" not in df.columns:
        raise KeyError(f"{path} must contain at least 'Entity' and 'Type'. Found: {list(df.columns)}")

    df["Type_norm"] = df["Type"].apply(normalize_type)
    df = df[df["Type_norm"].isin(PLACE_TYPES)].copy()
    df = df.drop(columns=["Type_norm"], errors="ignore")

    # de-duplicate rows to reduce calls; keep first occurrence (we'll merge back by Entity)
    df["Entity_normkey"] = df["Entity"].astype(str).str.strip()
    df = df[df["Entity_normkey"] != ""].copy()
    return df


# ----------------------------
# LLM: suggest modern spelling
# ----------------------------
def run_batch(place_names: list[str]) -> str:
    prompt = (
        "You will be given a list of place names from historical texts around Dresden.\n"
        "Task: provide a modernized spelling (or best matching modern place name) likely to be within ~20km of Dresden.\n"
        "Return ONLY CSV with two columns: 'Original' and 'Suggested'.\n"
        "Rules:\n"
        "- Keep 'Original' EXACTLY as given.\n"
        "- Provide at most ONE suggestion per row.\n"
        "- If you cannot suggest a reasonable normalization/match, leave 'Suggested' empty.\n"
        "- Do not add any extra commentary.\n"
    )
    body = "\n".join(f"- {p}" for p in place_names)

    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You output only CSV, no prose."},
            {"role": "user", "content": f"{prompt}\nLocations:\n{body}"},
        ],
    )
    return resp.choices[0].message.content.strip()


def parse_model_csv(content: str) -> list[tuple[str, str]]:
    content = strip_code_fences(content)
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return []

    sample = "\n".join(lines[:5])
    delim = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.reader(lines, delimiter=delim)
    out = []
    for row in reader:
        row = [c.strip() for c in row]
        if not row:
            continue
        low = [c.lower() for c in row]
        if len(low) >= 2 and "original" in low[0] and "suggest" in low[1]:
            continue
        if len(row) == 1:
            out.append((row[0], ""))
        else:
            out.append((row[0], row[1]))
    return out


def suggest_modern_spellings(unique_places: list[str]) -> Dict[str, str]:
    """
    Returns dict Original -> Suggested (possibly empty).
    """
    all_pairs: list[tuple[str, str]] = []

    for i in range(0, len(unique_places), BATCH_SIZE):
        batch = unique_places[i : i + BATCH_SIZE]
        attempt = 0

        while True:
            try:
                attempt += 1
                content = run_batch(batch)
                pairs = parse_model_csv(content)

                lookup = {orig: sugg for orig, sugg in pairs}
                for orig in batch:
                    all_pairs.append((orig, (lookup.get(orig) or "").strip()))

                print(f"✅ LLM batch {i//BATCH_SIZE + 1} / {(len(unique_places) + BATCH_SIZE - 1)//BATCH_SIZE}")
                time.sleep(SLEEP_BETWEEN_CALLS)
                break

            except Exception as e:
                if is_api_limit_exceeded_error(e) and attempt <= MAX_RETRIES:
                    wait_minutes = 10 if attempt == 1 else 60
                    print(
                        f"⚠️ Rate limit/quota issue. Waiting {wait_minutes} minutes, then retrying "
                        f"(attempt {attempt}/{MAX_RETRIES})..."
                    )
                    time.sleep(wait_minutes * 60)
                    continue
                raise

    # audit file of suggestions (optional)
    with open(OUT_SUGGESTIONS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Original", "Suggested"])
        w.writerows(all_pairs)

    return {o: s for o, s in all_pairs}


# ----------------------------
# Nominatim with cache (verify + lat/lon)
# ----------------------------
def load_cache(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(path: Path, cache: Dict[str, Any]) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def nominatim_search(query: str, cache: Dict[str, Any], session: requests.Session) -> Dict[str, Any]:
    if query in cache:
        return cache[query]

    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}
    try:
        resp = session.get(NOMINATIM_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            result = {"status": "no_results", "lat": None, "lon": None, "display_name": None}
        else:
            lat = safe_float(data[0].get("lat"))
            lon = safe_float(data[0].get("lon"))
            result = {
                "status": "ok" if (lat is not None and lon is not None) else "error",
                "lat": lat,
                "lon": lon,
                "display_name": data[0].get("display_name"),
            }
    except Exception as e:
        result = {"status": "error", "lat": None, "lon": None, "display_name": f"{type(e).__name__}: {e}"}

    cache[query] = result
    return result


def geocode_if_near_dresden(name: str, cache: Dict[str, Any], session: requests.Session) -> Tuple[str, Optional[float], Optional[float], str]:
    """
    Try several locally-biased queries and accept first within radius.
    Returns (status, lat, lon, used_query)
    """
    candidates = []
    name = (name or "").strip()
    if not name:
        return ("empty", None, None, "")

    # bias around Dresden to reduce false positives
    candidates.extend([f"{name}, Dresden", f"{name}, Saxony", f"{name}, Germany", name])

    last_status = "no_results"
    used = ""

    for q in candidates:
        used = q
        res = nominatim_search(q, cache, session)
        time.sleep(RATE_LIMIT_SECONDS)

        if res["status"] != "ok":
            last_status = res["status"]
            continue

        lat = res["lat"]
        lon = res["lon"]
        if lat is None or lon is None:
            last_status = "error"
            continue

        d = haversine_km(DRESDEN_LAT, DRESDEN_LON, float(lat), float(lon))
        if d <= RADIUS_KM:
            return ("ok", float(lat), float(lon), q)

        last_status = "out_of_radius"

    return (last_status, None, None, used)


# ----------------------------
# Append to data_for_qgis_v1.csv
# ----------------------------
def ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df


def main() -> None:
    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input: {INFILE.resolve()}")

    # 1) Read places_not_geolocated.csv and filter to place types
    df = read_places_not_geolocated(INFILE)
    if df.empty:
        print("No place rows in places_not_geolocated.csv after filtering (Place/Location/LOC).")
        return

    # Unique list for the LLM (reduces token usage/calls)
    unique_places = df["Entity_normkey"].drop_duplicates().tolist()

    # 2) LLM suggests modern spellings (writes API_unknown_places.csv as audit)
    suggestions = suggest_modern_spellings(unique_places)

    # 3) Geocode suggested spellings (Nominatim) and keep only within 20km
    cache = load_cache(CACHE_PATH)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: Dict[str, Dict[str, str]] = {}  # Entity -> fields

    for idx, ent in enumerate(unique_places, 1):
        suggested = (suggestions.get(ent) or "").strip()
        # If LLM couldn't suggest, try original as fallback
        query_name = suggested if suggested else ent

        status, lat, lon, used_query = geocode_if_near_dresden(query_name, cache, session)

        if status == "ok" and lat is not None and lon is not None:
            results[ent] = {
                "latitude": str(lat),
                "longitude": str(lon),
                "geocode_query": used_query,
                "geocode_status": "ok",
            }

        print(f"[{idx:>4}/{len(unique_places)}] {ent} -> {status} (suggested='{suggested}')")

    save_cache(CACHE_PATH, cache)

    if not results:
        print("No places could be geocoded within 20km of Dresden.")
        return

    # Merge geocode results back to all rows
    df["latitude_new"] = df["Entity_normkey"].map(lambda e: results.get(e, {}).get("latitude", ""))
    df["longitude_new"] = df["Entity_normkey"].map(lambda e: results.get(e, {}).get("longitude", ""))
    df["geocode_query_new"] = df["Entity_normkey"].map(lambda e: results.get(e, {}).get("geocode_query", ""))
    df["geocode_status_new"] = df["Entity_normkey"].map(lambda e: results.get(e, {}).get("geocode_status", ""))

    newly = df[df["geocode_status_new"] == "ok"].copy()
    if newly.empty:
        print("No rows marked ok after merge (unexpected).")
        return

    # Fill/overwrite geocode fields
    newly["latitude"] = newly["latitude_new"]
    newly["longitude"] = newly["longitude_new"]
    newly["geocode_query"] = newly["geocode_query_new"]
    newly["geocode_status"] = newly["geocode_status_new"]

    newly = newly.drop(
        columns=["Entity_normkey", "latitude_new", "longitude_new", "geocode_query_new", "geocode_status_new"],
        errors="ignore",
    )

    # 4) Append to data_for_qgis_v1.csv and de-duplicate
    if OUT_QGIS.exists():
        data = pd.read_csv(OUT_QGIS, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        data.columns = [clean_colname(c) for c in data.columns]
    else:
        data = pd.DataFrame()

    data = ensure_columns(data, list(newly.columns))
    newly = ensure_columns(newly, list(data.columns))

    combined = pd.concat([data, newly], ignore_index=True)

    # de-duplicate best-effort
    for c in ["Entity", "latitude", "longitude", "source_file_stem"]:
        if c not in combined.columns:
            combined[c] = ""
    combined = combined.drop_duplicates(subset=["Entity", "latitude", "longitude", "source_file_stem"], keep="first")

    combined.to_csv(OUT_QGIS, index=False, encoding="utf-8")
    print(f"✅ Appended {len(newly)} rows to {OUT_QGIS} (total now {len(combined)}).")


if __name__ == "__main__":
    main()
