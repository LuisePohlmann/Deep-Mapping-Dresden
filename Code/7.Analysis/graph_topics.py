import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# SETTINGS
# ==========================================
INPUT_FILE = r"Data\Analysis\bertopic_sentences_with_topics.csv"
OUTPUT_CSV = r"Data\Analysis\bertopic_top10_topics_50_year_periods_normalized.csv"
OUTPUT_PLOT = r"Data\Analysis\bertopic_top10_topics_50_year_linegraph_normalized.png"

TOP_N_TOPICS = 8
PERIOD_SIZE = 50

# ==========================================
# LOAD DATA
# ==========================================
df = pd.read_csv(INPUT_FILE, sep="|")


# ==========================================
# TOPIC LABELS
# ==========================================
TOPIC_LABELS = {
    0: "Umliegd. Dörfer, Schulen",
    1: "Theater/ Oper",
    2: "Natur/ die Elbe",
    5: "Vgl. mit anderen Städten",
    6: "Kirchen",
    7: "Kunstgallerie/ Zwinger",
    8: "Urban Life, Promenades, and Public Sociability",
    10: "Early Modern Historiography and Origins of Dresden",
    11: "Stadtteile",
    12: "Pillnitz, Hoftheater"
}

# ==========================================
# CLEAN DATA
# ==========================================
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["bertopic_topic"] = pd.to_numeric(
    df["bertopic_topic"],
    errors="coerce"
)

df = df.dropna(subset=["Year", "bertopic_topic"]).copy()

df["Year"] = df["Year"].astype(int)
df["bertopic_topic"] = df["bertopic_topic"].astype(int)

# ==========================================
# EXCLUDE BAD TOPICS
# ==========================================
EXCLUDED_TOPICS = [3, 4, 8, 9, 10]

df = df[
    (~df["bertopic_topic"].isin(EXCLUDED_TOPICS)) &
    (df["bertopic_topic"] != -1)
].copy()

# ==========================================
# FIND TOP 10 TOPICS
# ==========================================
top_topics = (
    df["bertopic_topic"]
    .value_counts()
    .head(TOP_N_TOPICS)
    .index
    .tolist()
)

plot_df = df[
    df["bertopic_topic"].isin(top_topics)
].copy()

# ==========================================
# CREATE 50-YEAR PERIODS
# ==========================================
plot_df["period_start"] = (
    plot_df["Year"] // PERIOD_SIZE
) * PERIOD_SIZE

plot_df["period_label"] = (
    plot_df["period_start"].astype(str)
    + "–"
    + (plot_df["period_start"] + PERIOD_SIZE - 1).astype(str)
)

# ==========================================
# TOTAL SENTENCES PER PERIOD
# (for normalization)
# ==========================================
total_sentences = (
    plot_df.groupby("period_start")
    .size()
    .reset_index(name="total_sentences")
)

# Need period_start in full dataframe too
plot_df["period_start"] = (
    plot_df["Year"] // PERIOD_SIZE
) * PERIOD_SIZE

# ==========================================
# COUNT TOPIC SENTENCES PER PERIOD
# ==========================================
counts = (
    plot_df
    .groupby(
        ["period_start", "period_label", "bertopic_topic"]
    )
    .size()
    .reset_index(name="topic_sentence_count")
)

# ==========================================
# MERGE TOTAL COUNTS
# ==========================================
counts = counts.merge(
    total_sentences,
    on="period_start",
    how="left"
)

# ==========================================
# CREATE COMPLETE TOPIC-PERIOD GRID
# ==========================================
all_periods = sorted(plot_df["period_start"].unique())
all_topics = sorted(top_topics)

full_index = pd.MultiIndex.from_product(
    [all_periods, all_topics],
    names=["period_start", "bertopic_topic"]
)

counts = counts.set_index(
    ["period_start", "bertopic_topic"]
).reindex(full_index).reset_index()

# Fill missing values
counts["topic_sentence_count"] = counts["topic_sentence_count"].fillna(0)
counts["total_sentences"] = counts["total_sentences"].fillna(method="ffill")

# Recreate labels
counts["period_label"] = (
    counts["period_start"].astype(int).astype(str)
    + "–"
    + (
        counts["period_start"].astype(int)
        + PERIOD_SIZE - 1
    ).astype(str)
)

# ==========================================
# NORMALIZE
# ==========================================
counts["normalized_frequency"] = (
    counts["topic_sentence_count"]
    / counts["total_sentences"]
)

# ==========================================
# CUMULATIVE SUM
# ==========================================
counts = counts.sort_values(
    by=["bertopic_topic", "period_start"]
)

counts["cumulative_frequency"] = (
    counts.groupby("bertopic_topic")[
        "normalized_frequency"
    ].cumsum()
)

# ==========================================
# PIVOT FOR PLOTTING
# ==========================================
pivot_counts = counts.pivot_table(
    index="period_start",
    columns="bertopic_topic",
    values="cumulative_frequency",
    fill_value=0
).sort_index()

# ==========================================
# SAVE CSV
# ==========================================
counts.to_csv(
    OUTPUT_CSV,
    sep="|",
    index=False,
    encoding="utf-8"
)

# ==========================================
# PLOT
# ==========================================
plt.figure(figsize=(14, 8))

for topic in pivot_counts.columns:

    plt.plot(
        pivot_counts.index,
        pivot_counts[topic],
        marker="o",
        linewidth=2,
        label=TOPIC_LABELS.get(topic, f"Topic {topic}")
    )

# ==========================================
# LABELS
# ==========================================
plt.xlabel("50-year period")
plt.ylabel("Cumulative normalized frequency")
plt.title(
    "Cumulative Normalized Topic Frequency Over Time"
)

plt.xticks(
    pivot_counts.index,
    [
        f"{year}–{year + PERIOD_SIZE - 1}"
        for year in pivot_counts.index
    ],
    rotation=45,
    ha="right"
)

plt.grid(True, alpha=0.3)

plt.legend(
    title="BERTopic Topic",
    bbox_to_anchor=(1.05, 1),
    loc="upper left"
)

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

print(f"Saved counts to: {OUTPUT_CSV}")
print(f"Saved plot to: {OUTPUT_PLOT}")
print(f"Top topics included: {top_topics}")