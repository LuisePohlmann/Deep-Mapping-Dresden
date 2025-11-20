import requests
import csv
from bs4 import BeautifulSoup

def scrape_reports_table(place_url, csv_path):
    resp = requests.get(place_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find heading "Erscheint in folgenden Berichten"
    heading = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and 
                        "Erscheint in folgenden Berichten" in tag.text)
    if not heading:
        raise ValueError("Could not find heading 'Erscheint in folgenden Berichten'")

    table = heading.find_next("table")
    if not table:
        raise ValueError("Could not find table after the heading")

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    # Add extra column for links
    # Only if the table includes a "Seite" / "Seiten" column
    if any("Seite" in h for h in headers):
        headers.append("Seiten-Links")

    rows = []

    # Extract row data
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if not tds:
            continue

        row = [td.get_text(strip=True) for td in tds]

        # Find the column that contains "Seite" or "Seiten"
        seite_col_index = None
        for i, h in enumerate(headers):
            if "Seite" in h:
                seite_col_index = i
                break

        # Extract all links from that cell
        if seite_col_index is not None and seite_col_index < len(tds):
            link_tags = tds[seite_col_index].find_all("a")
            links = [a["href"] for a in link_tags if a.has_attr("href")]
            row.append("; ".join(links))
        else:
            row.append("")

        rows.append(row)

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {csv_path}")


if __name__ == "__main__":
    scrape_reports_table(
        "https://reise.isgv.de/places/Q1731",
        "Q1731_reports_with_links.csv"
    )
