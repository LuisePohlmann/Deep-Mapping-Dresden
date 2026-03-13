# Generate the citations for the travelogues that were used in the style: Author. Year. Title. Link (=Citable_Url)

import pandas as pd

# Load dataset
df = pd.read_csv("places_dresden_combined_with_sentences_with_osm_flag.csv", sep="|")

# Keep unique combinations of Title + Link instead of Title only
df_unique = df.drop_duplicates(subset=["Title", "Citable_URL"])
print(len(df_unique), "unique citations found.")

# Sort by Author → Year → Title (nice bibliographic order)
df_unique = df_unique.sort_values(by=["Author", "Year", "Title"])

# Build bibliography lines
bib_lines = []

for _, row in df_unique.iterrows():

    author = str(row["Author"]).strip()
    year = str(int(row["Year"])) if str(row["Year"]).isdigit() else str(row["Year"])
    title = str(row["Title"]).strip()

    # Some datasets use Citable_URL or Link — handle both
    link = ""
    if "Citable_URL" in df.columns and pd.notna(row.get("Citable_URL")):
        link = str(row["Citable_URL"])
    elif "Link" in df.columns and pd.notna(row.get("Link")):
        link = str(row["Link"])

    citation = f"{author}. {year}. {title}. {link}"
    bib_lines.append(citation)

# Write to text file (one citation per line)
with open("bibliography.txt", "w", encoding="utf-8") as f:
    for line in bib_lines:
        f.write(line + "\n")


print("Bibliography exported to bibliography.txt")
print(f"Total unique citations: {len(bib_lines)}")
