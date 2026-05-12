import pandas as pd
import spacy
from spacytextblob.spacytextblob import SpacyTextBlob

INPUT_FILE = r"Data\places_dresden_combined_with_sentences_with_osm_flag.csv"
OUTPUT_FILE = r"Data\author_sentiment_summary.csv"

df = pd.read_csv(INPUT_FILE, sep="|")

nlp = spacy.load("de_dep_news_trf")
nlp.add_pipe("spacytextblob")

def get_sentiment(text):
    if pd.isna(text) or str(text).strip() == "":
        return None

    doc = nlp(str(text))
    return doc._.blob.polarity

df["sentiment_score"] = df["Full Sentence"].apply(get_sentiment)

author_sentiment = (
    df.groupby("Author")["sentiment_score"]
    .agg(
        average_sentiment="mean",
        sentiment_variance="var",
        sentiment_std="std",
        sentence_count="count"
    )
    .reset_index()
)

author_sentiment.to_csv(OUTPUT_FILE, sep="|", index=False)

print(author_sentiment.head(20))
print(f"\nSaved results to: {OUTPUT_FILE}")