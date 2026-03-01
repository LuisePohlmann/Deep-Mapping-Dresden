#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_CACHE_NAME = ".nominatim_cache.json"

# Load .env from current working dir (and parents if your shell sets it up)
load_dotenv()

# IMPORTANT: support BOTH lowercase and uppercase env var names
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT")
EMAIL = os.getenv("NOMINATIM_EMAIL")


def is_nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and pd.isna(v):
        return False
    return str(v).strip() != ""


def find_col(df: pd.DataFrame, name: str) -> Optional[str]:
    """Find a column by case-insensitive exact match."""
    target = name.strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == target:
            return c
    return None


def find_first_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first column found (case-insensitive exact match) from a list of candidates."""
    for name in candidates:
        c = find_col(df, name)
        if c:
            return c
    return None


def query_from_wikipedia_link(link: str) -> str:
    """
    Extract a decent query string from a Wikipedia URL path, e.g.
    https://de.wikipedia.org/wiki/Neustadt_(Dresden) -> 'Neustadt (Dresden)'
    """
    link = urllib.parse.unquote(str(link).strip())
    parsed = urllib.parse.urlparse(link)

    # If it's not a URL, just return the raw text
    if not parsed.scheme and not parsed.netloc:
        return link.strip()

    path = parsed.path.strip("/")
    if not path:
        return parsed.netloc

    last = path.split("/")[-1].split("#", 1)[0]
    return last.replace("_", " ").strip() or parsed.netloc


def load_cache(cache_path: str) -> Dict[str, Dict[str, Any]]:
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_cache(cache_path: str, cache: Dict[str, Dict[str, Any]]) -> None:
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, cache_path)


@dataclass
class NominatimClient:
    user_agent: str
    email: Optional[str]
    throttle_seconds: float = 1.0
    cache: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        self.session = requests.Session()
        self.cache = self.cache or {}
        self._last_ts = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_ts
        if elapsed < self.throttle_seconds:
            time.sleep(self.throttle_seconds - elapsed)
        self._last_ts = time.time()

    def geocode(self, q: str) -> Tuple[Optional[float], Optional[float], str]:
        """
        Returns (lat, lon, status).
        status in: ok | no_results | error
        """
        q_norm = " ".join(str(q).strip().split())
        if not q_norm:
            return None, None, "error"

        if q_norm in self.cache:
            c = self.cache[q_norm]
            return c.get("lat"), c.get("lon"), c.get("status", "no_results")

        self._throttle()

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "de,en;q=0.8",
        }

        params = {"q": q_norm, "format": "jsonv2", "limit": 1}
        if self.email:
            params["email"] = self.email

        try:
            r = self.session.get(NOMINATIM_URL, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception:
            self.cache[q_norm] = {"lat": None, "lon": None, "status": "error"}
            return None, None, "error"

        if not data:
            self.cache[q_norm] = {"lat": None, "lon": None, "status": "no_results"}
            return None, None, "no_results"

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        self.cache[q_norm] = {"lat": lat, "lon": lon, "status": "ok"}
        return lat, lon, "ok"


# === NEW: which labels count as place-like? Extend as needed.
PLACE_TYPES = {"location", "loc", "place"}


def normalize_type(v: Any) -> str:
    """Normalize an entity type cell to a comparable label."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip().lower()

    # Optional: map some common variations
    aliases = {
        "gpe": "location",
        "geo": "location",
        "geopolitical entity": "location",
        "locations": "location",
        "places": "place",
    }
    return aliases.get(s, s)


def process_csv(path: str, client: NominatimClient) -> bool:
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[SKIP] {path}: failed to read CSV ({e})")
        return False

    # Try to find key columns (robust to your different exports)
    entity_col = find_first_col(df, ["Entity", "entity", "Text", "text", "Span", "span", "Mention", "mention", "Name", "name"])
    type_col = find_first_col(df, ["Type", "type", "Label", "label", "EntityType", "entity_type", "NE_Type", "ne_type", "Tag", "tag", "Category", "category", "Class", "class"])

    # Link is optional now
    link_col = find_first_col(df, ["Link", "link", "URL", "url", "Wikipedia", "wikipedia"])
    if not link_col:
        # fallback: any column containing 'link' or 'wiki'
        for c in df.columns:
            lc = str(c).lower()
            if "link" in lc or "wiki" in lc:
                link_col = c
                break

    if not type_col:
        print(f"[SKIP] {path}: no type column found (tried Type/Label/EntityType/...)")
        return False

    # Ensure output columns exist
    for col in ["latitude", "longitude", "geocode_query", "geocode_status"]:
        if col not in df.columns:
            df[col] = pd.NA

    # Select rows whose type is Location/LOC/Place (case-insensitive)
    types_norm = df[type_col].apply(normalize_type)
    rows = df[types_norm.isin(PLACE_TYPES)].index

    if len(rows) == 0:
        print(f"[OK] {path}: no rows with type in {sorted(PLACE_TYPES)} (column: {type_col})")
        return False

    changed = False
    checked = 0
    skipped_no_query = 0

    for i in rows:
        # Skip if already filled
        if is_nonempty(df.at[i, "latitude"]) and is_nonempty(df.at[i, "longitude"]):
            continue

        q = None
        if entity_col and is_nonempty(df.at[i, entity_col]):
            q = str(df.at[i, entity_col]).strip()
        elif link_col and is_nonempty(df.at[i, link_col]):
            q = query_from_wikipedia_link(df.at[i, link_col])

        if not q:
            skipped_no_query += 1
            continue

        lat, lon, status = client.geocode(q)
        df.at[i, "geocode_query"] = q
        df.at[i, "geocode_status"] = status
        df.at[i, "latitude"] = lat
        df.at[i, "longitude"] = lon
        changed = True
        checked += 1

    if changed:
        df.to_csv(path, index=False)
        print(f"[WRITE] {path} ({checked} place-like rows geocoded; {skipped_no_query} skipped: no query source)")
        return True

    print(f"[OK] {path}: nothing to update ({len(rows)} candidate place-like rows; {skipped_no_query} skipped: no query source)")
    return False


def iter_csv_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".csv"):
                yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="NER", help="Root folder (default: NER)")
    ap.add_argument("--throttle", type=float, default=1.0, help="Seconds between requests (>=1 recommended)")
    args = ap.parse_args()

    cache_path = os.path.join(args.root, DEFAULT_CACHE_NAME)
    cache = load_cache(cache_path)

    if not USER_AGENT or "unknown" in str(USER_AGENT).lower():
        print("[WARN] User-Agent looks generic or missing. Set NOMINATIM_USER_AGENT in .env for best results.")
        # Nominatim requires a valid UA; don't silently proceed with None
        if not USER_AGENT:
            raise SystemExit("Missing NOMINATIM_USER_AGENT. Please set it in your environment or .env.")

    client = NominatimClient(
        user_agent=USER_AGENT,
        email=EMAIL,
        throttle_seconds=max(1.0, args.throttle),
        cache=cache,
    )

    csvs = list(iter_csv_files(args.root))
    if not csvs:
        print(f"[DONE] No CSV files found under {args.root}")
        return

    for p in csvs:
        _ = process_csv(p, client)
        # Save cache after each file so you can resume safely
        save_cache(cache_path, client.cache)

    print(f"[DONE] Cache saved to {cache_path}")


if __name__ == "__main__":
    main()
