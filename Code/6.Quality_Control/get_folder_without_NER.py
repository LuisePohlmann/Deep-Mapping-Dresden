import pandas as pd
from pathlib import Path

df = pd.read_csv("Data/Geolocation_Metadata/full_places_dresden.csv", sep="|", encoding="utf-8")

# Extract unique folder names from the "Subfolder" column
unique_folders = df["Subfolder"].dropna().unique()
#comapre with folders in images_of_pages
images_root = Path("Data/NER")
existing_folders = {p.name for p in images_root.iterdir() if p.is_dir()}

# Find folders that are in the images_of_pages but not in the metadata
missing_folders = existing_folders - set(unique_folders)

#save as txt file (one folder name per line)
with open("Data/Geolocation_Metadata/missing_folders.txt", "w", encoding="utf-8") as f:
    for folder in sorted(missing_folders):
        f.write(folder + "\n")

print(f"Folders in NER but not in metadata: {len(missing_folders)}")
print(missing_folders)

