# FInd folders with no mentions

# normalize spellings of "Dresden" 

#check "Brücke"

#check "großer garten"

#check Herberge

#not geolocated??

import pandas as pd

# Load dataset
df = pd.read_csv("places_dresden_combined_with_sentences_with_osm_flag.csv", sep="|")

weird_characters = df[df["Full Sentence"].str.contains(r"script=Han", regex=True, na=False)]

weird_characters.to_csv("Errors/weird_chracters.csv", sep="|")

# Find entities that only appear once
only_once = df[df["Entity"].isin(df["Entity"].value_counts()[df["Entity"].value_counts() == 1].index)]
only_once.to_csv("Errors/only_once.csv", sep="|")

