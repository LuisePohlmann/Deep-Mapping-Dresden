#Adds the full sentence, which the place appears in. Take the Entity column and find it the correct .txt file in the texts subfiolder. 
#Then extract the full sentence (from fullstop to fullstop) and save to full_places_dresden.csv

#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

IN_CSV = Path(r"Data/Geolocation_Metadata/places_dresden_combined_with_metadata.csv")
OUT_CSV = Path(r"Data/Geolocation_Metadata/places_dresden_combined_with_sentences.csv")
TEXTS_ROOT = Path("Data/texts")
NER_ERRORS_CSV = Path(r"Data/Geolocation_Metadata/NER_errors_round_2.csv")

SEP_IN = "|"
SEP_OUT = "|"


def load_spacy():
    try:
        import spacy  # type: ignore
        try:
            nlp = spacy.load("de_core_news_sm")
        except Exception:
            nlp = spacy.blank("de")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp
    except Exception:
        return None


def sort_page_files(files: List[Path]) -> List[Path]:
    def key(p: Path):
        stem = p.stem.strip()
        if stem.isdigit():
            return (0, int(stem))
        m = re.match(r"^\d+", stem)
        if m:
            return (1, int(m.group(0)))
        return (2, stem.lower())
    return sorted(files, key=key)


def normalize_linebreaks(text: str) -> str:
    """Remove line breaks from text.

    Line breaks are replaced with a space, except after hyphens where the
    hyphen and line break are joined without a space (e.g. "inter-\nnational"
    becomes "inter-national").
    """
    # Handle hyphenated line endings: join without space
    text = re.sub(r"-\s*\n\s*", "-", text)
    # Then collapse remaining newlines to spaces
    text = re.sub(r"\n+", " ", text)
    return text.strip()


def stitch_folder_text(folder_path: Path) -> str:
    txt_files = sort_page_files([p for p in folder_path.glob("*.txt") if p.is_file()])
    chunks: List[str] = []
    for fp in txt_files:
        content = fp.read_text(encoding="utf-8", errors="ignore")
        # normalize internal line breaks before concatenating pages
        content = normalize_linebreaks(content)
        chunks.append(content)
        chunks.append("\n\n[PAGE_BREAK]\n\n")
    return "".join(chunks)


ENUM_DOT_RE = re.compile(r"^\d+\.$")


def extract_sentence_spacy(nlp, text: str, start_idx: int) -> str:
    doc = nlp(text)
    sents = list(doc.sents)

    chosen_i = None
    for i, s in enumerate(sents):
        if s.start_char <= start_idx < s.end_char:
            chosen_i = i
            break
    if chosen_i is None:
        return ""

    s = sents[chosen_i]
    s_text = s.text.strip()

    # Fix: enumerator-only sentence like "1." should merge with next
    if ENUM_DOT_RE.match(s_text) and chosen_i + 1 < len(sents):
        merged = (s.text + " " + sents[chosen_i + 1].text).strip()
        return " ".join(merged.split())

    return " ".join(s_text.split())


def find_entity_span(text: str, entity: str, start_from: int = 0):
    ent = entity.strip()
    if not ent:
        return None

    # Prefer word boundary match for alphabetic entities
    if re.fullmatch(r"[A-Za-zÄÖÜäöüßſ\- ]+", ent):
        pat = re.compile(rf"(?i)\b{re.escape(ent)}\b")
        m = pat.search(text, pos=start_from)
    else:
        m = re.search(re.escape(ent), text[start_from:], flags=re.IGNORECASE)
        if m:
            return (start_from + m.start(), start_from + m.end())
        return None

    if not m:
        return None

    return (m.start(), m.end())


def main() -> int:
    if not IN_CSV.exists():
        raise FileNotFoundError(f"Missing input: {IN_CSV.resolve()}")
    if not TEXTS_ROOT.exists():
        raise FileNotFoundError(f"Missing texts root folder: {TEXTS_ROOT.resolve()}")

    df = pd.read_csv(IN_CSV, sep=SEP_IN, dtype=str, encoding="utf-8").fillna("")
    if "Entity" not in df.columns:
        raise KeyError("Input CSV must contain an 'Entity' column.")

    folder_col = None
    for cand in ("Subfolder", "Folder"):
        if cand in df.columns:
            folder_col = cand
            break
    if folder_col is None:
        raise KeyError("Need a column 'Subfolder' or 'Folder' to locate the correct texts subfolder.")

    nlp = load_spacy()
    if nlp is None:
        raise RuntimeError("spaCy not available. Install spaCy + a German model (e.g., de_core_news_sm).")

    # Cache full stitched text per folder
    stitched_cache: Dict[str, str] = {}
    # NEW: per-folder cursor, so repeated access finds the next mention
    folder_cursor: Dict[str, int] = {}

    sentences: List[str] = []

    valid_rows = []
    error_rows = []

    for _, row in df.iterrows():
        folder = str(row.get(folder_col, "")).strip()

        historical = str(row.get("historical spelling", "")).strip()
        entity = str(row.get("Entity", "")).strip()
        
        # Primary search value (prefer historical spelling if available)
        search_value = historical if historical else entity

        if not folder or not search_value:
            error_rows.append(row)
            continue

        folder_path = TEXTS_ROOT / folder
        if not folder_path.exists():
            error_rows.append(row)
            continue

        if folder not in stitched_cache:
            stitched_cache[folder] = stitch_folder_text(folder_path)
            folder_cursor[folder] = 0

        text = stitched_cache[folder]
        start_from = folder_cursor.get(folder, 0)

        span = find_entity_span(text, search_value, start_from=start_from)
        if not span:
            span = find_entity_span(text, search_value, start_from=0)
        
        # If primary search fails, try the alternative value
        if not span:
            alternative = entity if search_value == historical else historical
            if alternative and alternative != search_value:
                span = find_entity_span(text, alternative, start_from=start_from)
                if not span:
                    span = find_entity_span(text, alternative, start_from=0)

        if not span:
            # ❌ Entity not found → move to error dataset
            error_rows.append(row)
            continue

        folder_cursor[folder] = span[1]
        
        sent = extract_sentence_spacy(nlp, text, span[0])
        # Normalize line breaks: remove hyphens + newlines, replace remaining newlines with spaces
        sent = normalize_linebreaks(sent)
        
        row_copy = row.copy()
        row_copy["Full Sentence"] = sent
        valid_rows.append(row_copy)

        df_valid = pd.DataFrame(valid_rows)
        df_errors = pd.DataFrame(error_rows)

        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

        df_valid.to_csv(OUT_CSV, sep=SEP_OUT, index=False, encoding="utf-8")
        print(f"✅ Wrote valid rows: {OUT_CSV} ({len(df_valid)} rows)")

        if not df_errors.empty:
            df_errors.to_csv(NER_ERRORS_CSV, sep=SEP_OUT, index=False, encoding="utf-8")
            print(f"⚠️ Wrote NER errors: {NER_ERRORS_CSV} ({len(df_errors)} rows)")
        else:
            print("No NER errors found.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise