import pandas as pd
import re
from pathlib import Path

# Paths
input_path = Path("Data/Data_hand_normalized.xlsx")
output_path = Path("Errors/weird_characters_2.csv")

# Ensure output directory exists
output_path.parent.mkdir(parents=True, exist_ok=True)

# Load data
df = pd.read_excel(input_path)

# Regex pattern for allowed German characters
allowed_pattern = re.compile(r'^[A-Za-z0-9äöüÄÖÜß\s.,;:!?\'"()\-\[\]{}\\/]+$')

def has_weird_characters(text):
    if pd.isna(text):
        return False
    return not bool(allowed_pattern.match(str(text)))

# Find rows with non-German characters
mask = df["Full Sentence"].apply(has_weird_characters)
weird_rows = df[mask]

# Save result
weird_rows.to_csv(output_path, index=False, encoding="utf-8")

print(f"Found {len(weird_rows)} rows with non-German characters.")
print(f"Saved to: {output_path}")