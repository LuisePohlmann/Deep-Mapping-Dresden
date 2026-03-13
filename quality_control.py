# Find folders with no mentions
import pandas as pd

df = pd.read_excel("Data/Data_hand_normalized.xlsx")

# Find rows containing Chinese characters
chinese_characters = df[df["Full Sentence"].str.contains(r"[\u4E00-\u9FFF]", regex=True, na=False)]

chinese_characters.to_csv("Errors/weird_characters.csv", sep="|", index=False)

