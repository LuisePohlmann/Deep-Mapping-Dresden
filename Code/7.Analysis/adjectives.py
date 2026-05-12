import pandas as pd
import spacy
import matplotlib.pyplot as plt
from collections import Counter

# ==========================================
# SETTINGS
# ==========================================
INPUT_FILE = r"Data\Analysis\bertopic_sentences_with_topics.csv"

OUTPUT_CSV = r"Data\Analysis\top15_adjective_frequency_timeline.csv"
OUTPUT_PLOT = r"Data\Analysis\top15_adjective_frequency_timeline.png"

TEXT_COLUMN = "Full Sentence"
YEAR_COLUMN = "Year"

TOP_N_ADJECTIVES = 15
PERIOD_SIZE = 50

# ==========================================
# LOAD DATA
# ==========================================
df = pd.read_csv(INPUT_FILE, sep="|")

df[YEAR_COLUMN] = pd.to_numeric(df[YEAR_COLUMN], errors="coerce")
df[TEXT_COLUMN] = df[TEXT_COLUMN].astype(str).str.strip()

df = df.dropna(subset=[YEAR_COLUMN, TEXT_COLUMN]).copy()
df[YEAR_COLUMN] = df[YEAR_COLUMN].astype(int)

# ==========================================
# LOAD SPACY
# ==========================================
print("Loading spaCy model...")
nlp = spacy.load("de_dep_news_trf")

# ==========================================
# EXTRACT ADJECTIVES
# ==========================================
print("Extracting adjectives...")

rows = []

for _, row in df.iterrows():
    year = row[YEAR_COLUMN]
    sentence = row[TEXT_COLUMN]

    doc = nlp(sentence)

    for token in doc:
        if token.pos_ == "ADJ":

            if (
                token.is_stop
                or token.is_punct
                or token.like_num
                or token.is_space
            ):
                continue

            adjective = token.lemma_.lower().strip()

            if len(adjective) > 2:
                rows.append({
                    "Year": year,
                    "Adjective": adjective
                })

adj_df = pd.DataFrame(rows)

# ==========================================
# FIND TOP 15 ADJECTIVES OVERALL
# ==========================================
top_adjectives = (
    adj_df["Adjective"]
    .value_counts()
    .head(TOP_N_ADJECTIVES)
    .index
    .tolist()
)

adj_df = adj_df[adj_df["Adjective"].isin(top_adjectives)].copy()

# ==========================================
# CREATE 50-YEAR PERIODS
# ==========================================
adj_df["period_start"] = (adj_df["Year"] // PERIOD_SIZE) * PERIOD_SIZE

adj_df["period_label"] = (
    adj_df["period_start"].astype(str)
    + "–"
    + (adj_df["period_start"] + PERIOD_SIZE - 1).astype(str)
)

# ==========================================
# COUNT ADJECTIVES PER PERIOD
# ==========================================
timeline_df = (
    adj_df
    .groupby(["period_start", "period_label", "Adjective"])
    .size()
    .reset_index(name="frequency")
)

timeline_df.to_csv(
    OUTPUT_CSV,
    sep="|",
    index=False,
    encoding="utf-8"
)

# ==========================================
# PIVOT FOR PLOTTING
# ==========================================
pivot_df = timeline_df.pivot_table(
    index="period_start",
    columns="Adjective",
    values="frequency",
    fill_value=0
).sort_index()

# ==========================================
# PLOT
# ==========================================
plt.figure(figsize=(14, 8))

for adjective in pivot_df.columns:
    plt.plot(
        pivot_df.index,
        pivot_df[adjective],
        marker="o",
        label=adjective
    )

plt.xlabel("50-year period")
plt.ylabel("Adjective frequency")
plt.title("Frequency Timeline of the 15 Most Used Adjectives")

plt.xticks(
    pivot_df.index,
    [
        f"{year}–{year + PERIOD_SIZE - 1}"
        for year in pivot_df.index
    ],
    rotation=45,
    ha="right"
)

plt.grid(True, alpha=0.3)

plt.legend(
    title="Adjective",
    bbox_to_anchor=(1.05, 1),
    loc="upper left"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_PLOT,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print(f"Saved timeline data to: {OUTPUT_CSV}")
print(f"Saved plot to: {OUTPUT_PLOT}")
print(f"Top adjectives: {top_adjectives}")