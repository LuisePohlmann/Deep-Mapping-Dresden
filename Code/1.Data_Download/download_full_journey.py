import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

input_file = r"Data\Data_hand_normalized.xlsx"
output_file = r"Data\journey_places.csv"

# Read Excel
df = pd.read_excel(input_file)

# Get unique URLs
urls = df["Citable_URL"].dropna().unique()

results = []

for url in urls:
    try:
        print(f"Opening {url}")

        response = requests.get(url, timeout=20)
        response.raise_for_status()
        response.encoding = "utf-8" 

        soup = BeautifulSoup(response.text, "html.parser")

        places = []
        for g in soup.select("g.svg-place-group"):
            texts = g.find_all("text")

            if len(texts) > 0:
                place_name = texts[0].get_text(strip=True)
                places.append(place_name)

        results.append({
            "URL": url,
            "Places": " | ".join(places)
        })

        time.sleep(1)

    except Exception as e:
        print(f"Error with {url}: {e}")
        results.append({
            "URL": url,
            "Places": None
        })

# Save results
out_df = pd.DataFrame(results)
out_df.to_csv(output_file, index=False, sep="|", encoding="utf-8")

print("Done.")