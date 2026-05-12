import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# SETTINGS
# ==========================================
SENTIMENT_FILE = r"Data\author_sentiment_summary.csv"
METADATA_FILE = r"Data\Raw_Metadata\travelogues_full_metadata_with_images.csv"

OUTPUT_CSV = r"Data\author_sentiment_summary_with_year.csv"
OUTPUT_PLOT = r"Data\author_sentiment_by_gender.png"

# ==========================================
# LOAD DATA
# ==========================================
sentiment_df = pd.read_csv(SENTIMENT_FILE, sep="|")
metadata_df = pd.read_csv(METADATA_FILE, sep="|")

# ==========================================
# REMOVE PLACEHOLDER AUTHOR
# ==========================================
sentiment_df = sentiment_df[
    sentiment_df["Author"].astype(str).str.strip() != "Kein Eintrag vorhanden"
].copy()

# ==========================================
# PREPARE METADATA
# ==========================================
metadata_subset = metadata_df[
    ["Author", "Year", "Gender"]
].copy()

sentiment_df["Author"] = sentiment_df["Author"].astype(str).str.strip()
metadata_subset["Author"] = metadata_subset["Author"].astype(str).str.strip()

# Keep only one row per author
metadata_subset = metadata_subset.drop_duplicates(
    subset=["Author"],
    keep="first"
)

# ==========================================
# MERGE DATA
# ==========================================
merged_df = sentiment_df.merge(
    metadata_subset,
    on="Author",
    how="left"
)

# Numeric conversion
merged_df["Year"] = pd.to_numeric(
    merged_df["Year"],
    errors="coerce"
)

merged_df["average_sentiment"] = pd.to_numeric(
    merged_df["average_sentiment"],
    errors="coerce"
)

merged_df["sentiment_std"] = pd.to_numeric(
    merged_df["sentiment_std"],
    errors="coerce"
)

# Remove incomplete rows
plot_df = merged_df.dropna(
    subset=["Year", "average_sentiment", "sentiment_std"]
).copy()

# ==========================================
# SAVE MERGED CSV
# ==========================================
merged_df.to_csv(OUTPUT_CSV, sep="|", index=False)

# ==========================================
# COLOR MAPPING
# ==========================================
gender_colors = {
    "male": "steelblue",
    "female": "darkred"
}

# ==========================================
# CREATE PLOT
# ==========================================
plt.figure(figsize=(12, 7))

for _, row in plot_df.iterrows():

    gender = str(row["Gender"]).strip().lower()

    color = gender_colors.get(gender, "gray")

    plt.errorbar(
        row["Year"],
        row["average_sentiment"],
        yerr=row["sentiment_std"],
        fmt="o",
        color=color,
        capsize=4,
        alpha=0.8
    )

# ==========================================
# CUSTOM LEGEND
# ==========================================
male_handle = plt.Line2D(
    [0], [0],
    marker='o',
    color='steelblue',
    linestyle='',
    label='Male'
)

female_handle = plt.Line2D(
    [0], [0],
    marker='o',
    color='darkred',
    linestyle='',
    label='Female'
)

plt.legend(handles=[male_handle, female_handle])

# ==========================================
# LABELS
# ==========================================
plt.xlabel("Year")
plt.ylabel("Average Sentiment")
plt.title("Average Sentiment by Year and Gender")

plt.grid(True, alpha=0.3)

plt.tight_layout()

# ==========================================
# SAVE + SHOW
# ==========================================
plt.savefig(
    OUTPUT_PLOT,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print(f"Saved merged data to: {OUTPUT_CSV}")
print(f"Saved plot to: {OUTPUT_PLOT}")