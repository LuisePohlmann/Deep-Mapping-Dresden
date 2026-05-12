import pandas as pd
import spacy
from collections import Counter
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# ==========================================
# SETTINGS
# ==========================================
INPUT_FILE = r"Data\places_dresden_combined_with_sentences_with_osm_flag.csv"

OUTPUT_SENTENCES = r"Data\Analysis\bertopic_sentences_with_topics.csv"
OUTPUT_TOPIC_INFO = r"Data\Analysis\bertopic_topic_info.csv"
OUTPUT_TOPIC_WORDLISTS = r"Data\Analysis\bertopic_topic_adjectives_noun_phrases.csv"

TEXT_COLUMN = "Full Sentence"

TOP_N = 50

# ==========================================
# LOAD DATA
# ==========================================
df = pd.read_csv(INPUT_FILE, sep="|")

df[TEXT_COLUMN] = df[TEXT_COLUMN].astype(str).str.strip()

df = df[
    df[TEXT_COLUMN].notna() &
    (df[TEXT_COLUMN] != "") &
    (df[TEXT_COLUMN].str.lower() != "nan")
].copy()

# ==========================================
# LOAD SPACY
# ==========================================
print("Loading spaCy model...")
nlp = spacy.load("de_dep_news_trf")

# ==========================================
# TEXT CLEANING FUNCTION
# ==========================================
def preprocess_text(text):

    doc = nlp(text)

    cleaned_tokens = []

    for token in doc:

        # Remove stopwords, punctuation, numbers, spaces
        if (
            token.is_stop
            or token.is_punct
            or token.like_num
            or token.is_space
        ):
            continue

        lemma = token.lemma_.lower().strip()

        # Remove tiny tokens
        if len(lemma) <= 2:
            continue

        cleaned_tokens.append(lemma)

    return " ".join(cleaned_tokens)

# ==========================================
# PREPROCESS SENTENCES
# ==========================================
print("Removing stopwords and preprocessing text...")

df["cleaned_sentence"] = [
    preprocess_text(text)
    for text in df[TEXT_COLUMN]
]

# Remove empty cleaned rows
df = df[
    df["cleaned_sentence"].str.strip() != ""
].copy()

sentences = df["cleaned_sentence"].tolist()

# ==========================================
# LOAD EMBEDDING MODEL
# ==========================================
print("Loading embedding model...")

embedding_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# ==========================================
# RUN BERTOPIC
# ==========================================
print("Running BERTopic...")

topic_model = BERTopic(
    embedding_model=embedding_model,
    language="multilingual",
    calculate_probabilities=True,
    verbose=True
)

topics, probabilities = topic_model.fit_transform(sentences)

df["bertopic_topic"] = topics

df["bertopic_probability"] = [
    max(prob) if prob is not None else None
    for prob in probabilities
]

# ==========================================
# SAVE SENTENCE OUTPUT
# ==========================================
df.to_csv(
    OUTPUT_SENTENCES,
    sep="|",
    index=False,
    encoding="utf-8"
)

# ==========================================
# SAVE TOPIC INFO
# ==========================================
topic_info = topic_model.get_topic_info()

topic_info.to_csv(
    OUTPUT_TOPIC_INFO,
    sep="|",
    index=False,
    encoding="utf-8"
)

# ==========================================
# EXTRACT ADJECTIVES + NOUN PHRASES PER TOPIC
# ==========================================
print("Extracting adjectives and noun phrases...")

topic_rows = []

for topic_id, group in df.groupby("bertopic_topic"):

    original_sentences = group[TEXT_COLUMN].tolist()

    adjective_counter = Counter()
    noun_phrase_counter = Counter()

    for doc in nlp.pipe(original_sentences, batch_size=50):

        # ------------------------------
        # ADJECTIVES
        # ------------------------------
        for token in doc:

            if token.pos_ == "ADJ":

                if (
                    token.is_stop
                    or token.is_punct
                    or token.like_num
                ):
                    continue

                adjective = token.lemma_.lower().strip()

                if len(adjective) > 2:
                    adjective_counter[adjective] += 1

        # ------------------------------
        # NOUN PHRASES
        # ------------------------------
        current_phrase = []

        for token in doc:

            if (
                token.pos_ in {"ADJ", "NOUN", "PROPN"}
                and not token.is_stop
                and not token.is_punct
            ):

                lemma = token.lemma_.lower().strip()

                if len(lemma) > 2:
                    current_phrase.append(lemma)

            else:

                if len(current_phrase) >= 1:
                    phrase = " ".join(current_phrase)

                    noun_phrase_counter[phrase] += 1

                current_phrase = []

        if len(current_phrase) >= 1:
            phrase = " ".join(current_phrase)

            noun_phrase_counter[phrase] += 1

    # ------------------------------
    # BERTOPIC KEYWORDS
    # ------------------------------
    topic_words = topic_model.get_topic(topic_id)

    if topic_words:
        bertopic_keywords = ", ".join(
            [word for word, score in topic_words[:10]]
        )
    else:
        bertopic_keywords = ""

    # ------------------------------
    # SAVE TOPIC ROW
    # ------------------------------
    topic_rows.append({
        "Topic": topic_id,
        "Number of Sentences": len(original_sentences),
        "BERTopic Keywords": bertopic_keywords,
        "Top Adjectives": "; ".join(
            [
                f"{word} ({count})"
                for word, count in adjective_counter.most_common(TOP_N)
            ]
        ),
        "Top Noun Phrases": "; ".join(
            [
                f"{phrase} ({count})"
                for phrase, count in noun_phrase_counter.most_common(TOP_N)
            ]
        )
    })

# ==========================================
# SAVE TOPIC WORDLISTS
# ==========================================
topic_wordlists_df = pd.DataFrame(topic_rows)

topic_wordlists_df = topic_wordlists_df.sort_values(by="Topic")

topic_wordlists_df.to_csv(
    OUTPUT_TOPIC_WORDLISTS,
    sep="|",
    index=False,
    encoding="utf-8"
)

print("Done!")
print(f"Saved sentence topics to: {OUTPUT_SENTENCES}")
print(f"Saved topic info to: {OUTPUT_TOPIC_INFO}")
print(f"Saved adjective/noun phrase lists to: {OUTPUT_TOPIC_WORDLISTS}")