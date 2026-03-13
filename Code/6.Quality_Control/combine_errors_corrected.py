#!/usr/bin/env python3
"""
Combines and corrects geolocation data from multiple sources:
1) NER_errors_corrected.csv, 2) unfound_in_folders.csv, 3) places_dresden_with_unkown.csv

Step 1: Set Certainty='certain' for rows without historical spelling
Step 2: Append unfound_in_folders.csv (align columns, set Certainty='certain')
Step 3: Update from NER_errors_corrected.csv where columns match (except Certainty)
"""

from pathlib import Path
import pandas as pd

# File paths
PLACES_DRESDEN = Path(r"Data/Geolocation_Metadata/places_dresden_with_unkown.csv")
UNFOUND_FOLDERS = Path(r"Data/Geolocation_Metadata/unfound_in_folders.csv")
NER_ERRORS = Path(r"Data/Geolocation_Metadata/NER_errors_corrected.csv")
OUT_CSV = Path(r"Data/Geolocation_Metadata/places_corrected_combined.csv")

SEP = "|"


def normalize_for_match(text: str) -> str:
    """Normalize text for matching: lowercase and ß → ss."""
    return text.strip().lower().replace("ß", "ss")


def main():
    # Load the main file
    if not PLACES_DRESDEN.exists():
        print(f"❌ {PLACES_DRESDEN} not found")
        return
    
    df_places = pd.read_csv(PLACES_DRESDEN, sep=SEP, dtype=str).fillna("")
    print(f"📖 Loaded {len(df_places)} rows from {PLACES_DRESDEN}")
    
    # ============================================================
    # Step 1: Set Certainty='certain' for rows without historical spelling
    # ============================================================
    empty_hist = df_places["historical spelling"].str.strip() == ""
    certainty_set_count = empty_hist.sum()
    df_places.loc[empty_hist, "Certainty"] = "certain"
    print(f"✅ Step 1: Set Certainty='certain' for {certainty_set_count} rows without historical spelling")
    
    # ============================================================
    # Step 2: Append unfound_in_folders.csv
    # ============================================================
    if UNFOUND_FOLDERS.exists():
        df_unfound = pd.read_csv(UNFOUND_FOLDERS, sep=SEP, dtype=str).fillna("")
        print(f"📖 Loaded {len(df_unfound)} rows from {UNFOUND_FOLDERS}")
        
        # Add missing columns to unfound dataframe
        for col in df_places.columns:
            if col not in df_unfound.columns:
                df_unfound[col] = ""
        
        # Reorder columns to match places_dresden
        df_unfound = df_unfound[df_places.columns]
        
        # Set Certainty to 'certain' for all unfound rows
        df_unfound["Certainty"] = "certain"
        
        # Append to main dataframe
        df_places = pd.concat([df_places, df_unfound], ignore_index=True)
        print(f"✅ Step 2: Appended {len(df_unfound)} rows from {UNFOUND_FOLDERS}")
        print(f"          Total rows now: {len(df_places)}")
    else:
        print(f"⚠️  {UNFOUND_FOLDERS} not found, skipping step 2")
    
    # ============================================================
    # Step 3: Update from NER_errors_corrected.csv
    # ============================================================
    if NER_ERRORS.exists():
        df_ner = pd.read_csv(NER_ERRORS, sep=SEP, dtype=str).fillna("")
        print(f"📖 Loaded {len(df_ner)} rows from {NER_ERRORS}")
        
        # Match rows where:
        # - NER "Entity" matches places "Entity" (normalized: case-insensitive, ß → ss)
        # - Subfolder matches
        # - SourceFileStem matches
        # Then update "historical spelling" with NER value
        updated_count = 0
        
        for idx, ner_row in df_ner.iterrows():
            ner_hist_spelling = ner_row.get("historical spelling", "").strip()
            ner_entity = ner_row.get("Entity", "").strip()
            ner_subfolder = ner_row.get("Subfolder", "").strip()
            ner_source_stem = ner_row.get("SourceFileStem", "").strip()
            
            if not ner_entity:
                continue
            
            # Normalize for flexible matching (case-insensitive, ß → ss)
            ner_entity_normalized = normalize_for_match(ner_entity)
            places_entity_normalized = df_places["Entity"].str.strip().str.lower().str.replace("ß", "ss")
            
            # Match on normalized NER "Entity" = places "Entity", Subfolder, and SourceFileStem
            mask = (places_entity_normalized == ner_entity_normalized)
            
            if ner_subfolder and "Subfolder" in df_places.columns:
                mask = mask & (df_places["Subfolder"].str.strip() == ner_subfolder)
            
            if ner_source_stem and "SourceFileStem" in df_places.columns:
                mask = mask & (df_places["SourceFileStem"].str.strip() == ner_source_stem)
            
            # Update historical spelling for matching rows
            if mask.any() and ner_hist_spelling:
                df_places.loc[mask, "historical spelling"] = ner_hist_spelling
                updated_count += mask.sum()
        
        print(f"✅ Step 3: Updated {updated_count} rows from {NER_ERRORS}")
    else:
        print(f"⚠️  {NER_ERRORS} not found, skipping step 3")
    
    # ============================================================
    # Save the result
    # ============================================================
    # Drop the Type column if it exists
    if "Type" in df_places.columns:
        df_places = df_places.drop(columns=["Type"])
        print("Dropped 'Type' column from final output")
    
    df_places.to_csv(OUT_CSV, sep=SEP, index=False, encoding="utf-8")
    print(f"🎉 Result written to {OUT_CSV} ({len(df_places)} rows)")


if __name__ == "__main__":
    main()
