import requests
from urllib.parse import urljoin
import argparse
import csv
from bs4 import BeautifulSoup

def scrape_reports_table(place_url, csv_path):
    resp = requests.get(place_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "html.parser")

    # Find heading "Erscheint in folgenden Berichten"
    heading = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and 
                        "Erscheint in folgenden Berichten" in tag.text)
    if not heading:
        raise ValueError("Could not find heading 'Erscheint in folgenden Berichten'")

    table = heading.find_next("table")
    if not table:
        raise ValueError("Could not find table after the heading")

    rows = []

    # Extract row data — include the first row unless it is a header row (<th>)
    for tr in table.find_all("tr"):
        # skip header rows that use <th>
        if tr.find_all("th"):
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        row = [td.get_text(strip=True) for td in tds]
        rows.append(row)

    # Write CSV
    output_headers = ["Year", "Title", "Pages"]
     # Save to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(output_headers)
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape reports table and save to CSV")
    parser.add_argument("url", nargs="?", default="https://reise.isgv.de/places/Q1731")
    parser.add_argument("output", nargs="?", default="Q1731_reports.csv")
    args = parser.parse_args()

    scrape_reports_table(args.url, args.output)
