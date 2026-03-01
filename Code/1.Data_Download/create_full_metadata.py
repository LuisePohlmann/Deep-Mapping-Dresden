#Combines the two metadata CSVs (author_traveltime + with_links) into one full metadata CSV, matching rows by Index and adding the Gender column
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd


AUTHOR_TRAVELTIME_CSV = Path("Data/Raw_Metadata/travelogues_author_traveltime.csv")
WITH_LINKS_CSV = Path("Data/Raw_Metadata/travelogues_with_links.csv")
OUT_CSV = Path("Data/Raw_Metadata/travelogues_full_metadata.csv")

# Input separators (as described)
SEP_AUTHOR = ";"   # Name;Autor;publikationsdatum;Reisedaten;...
SEP_LINKS = ";"    # Index;Year;Title;...

# Output separator
OUT_SEP = "|"

# --- Column name normalization helpers ---
def norm_col(c: str) -> str:
    # Remove BOM, trim, normalize whitespace
    return str(c).replace("\ufeff", "").strip()

def norm_title(s: str) -> str:
    # Normalize titles for matching (casefold + collapse whitespace)
    if pd.isna(s):
        return ""
    return " ".join(str(s).strip().split()).casefold()


def add_gender_column(df: pd.DataFrame,
                      female_names_path: str = "Data/Raw_Metadata/female_names.txt",
                      author_col: str = "Author") -> pd.DataFrame:
    """
    Adds a 'Gender' column to the dataframe.
    If the author's first name appears in female_names.txt → 'female'
    otherwise → 'male'
    """

    # Load female names (one per line)
    female_names = {
        line.strip().casefold()
        for line in Path(female_names_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    def detect_gender(author_name: str) -> str:
        if pd.isna(author_name):
            return "male"

        name = str(author_name).strip().casefold()
        return "female" if  name in female_names else "male"

    df["Gender"] = df[author_col].apply(detect_gender)

    return df

def main() -> int:
    df_a = pd.read_csv(AUTHOR_TRAVELTIME_CSV, sep=SEP_AUTHOR)
    df_l = pd.read_csv(WITH_LINKS_CSV, sep=SEP_LINKS)

    # Make sure meta has a clean 0..n-1 index, then turn it into a column for merging
    df_a = df_a.reset_index(drop=True)
    df_a["Index"] = df_a.index.astype(int).astype(str)  # string for safe merge

    # Clean df_links Index too
    df_l["Index"] = df_l["Index"].astype(str).str.strip()

    # Keep only rows present in df_links (authoritative)
    merged = df_l.merge(df_a, on="Index", how="left")

    # Validate required meta columns (if missing, create empty)
    for col in ["Reisedaten", "gesamtseitenzahl", "Digitalisat", "Zitierfähige URL"]:
        if col not in merged.columns:
            merged[col] = ""

    out = pd.DataFrame({
        "Index": merged["Index"],
        "Year": merged.get("Year", ""),
        "Title": merged.get("Title", ""),
        "Author": merged.get("Autor", ""),
        "Travel Period": merged.get("Reisedaten", ""),
        "Pages": merged.get("Pages", ""),
        "Full Page Count": merged.get("gesamtseitenzahl", ""),
        "Link": merged.get("Link", ""),
        "Folder": merged.get("Folder", ""),
        "Digitally Available at": merged.get("Digitalisat", ""),
        "Citable URL": merged.get("Zitierfähige URL", ""),
    }).fillna("")

    
    out = add_gender_column(out,  "Data/Raw_Metadata/female_names.txt", author_col="Author")

    out.to_csv(OUT_CSV, sep=OUT_SEP, index=False, encoding="utf-8")

    # Merge report
    total = len(out)
    matched = int((out["Travel Period"].astype(str).str.strip() != "").sum())
    print(f"Wrote {OUT_CSV} with {total} rows.")
    print(f"Matched metadata rows: {matched}/{total}")
    if matched < total:
        print("Note: Some rows had no matching metadata (Index not present in author_traveltime file).")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise