#!/usr/bin/env python3
"""
Print basic statistics about the reiseberichte project
based entirely on metadata.csv
"""
import csv
import os
from pathlib import Path
import re
from collections import Counter
import matplotlib.pyplot as plt
import statistics

METADATA_CSV = "metadata.csv"
IMAGES_DIR = "images"


def count_csv_rows(csv_file):
    """Count rows in CSV (excluding header)."""
    if not os.path.exists(csv_file):
        return 0
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        return sum(1 for _ in reader)


def count_folders(directory):
    """Count folders in a directory."""
    if not os.path.isdir(directory):
        return 0
    return len([
        d for d in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, d))
    ])


def count_total_images(directory):
    """Count total image files across all subdirectories."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.jp2'}
    total = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                total += 1
    return total


def count_authors_and_unique_cite(metadata_csv):
    """Return (author_entries, unique_authors, unique_cite_urls)."""
    authors = []
    cite_urls = set()

    with open(metadata_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            autor = (row.get('Autor') or '').strip()
            if autor:
                authors.append(autor)

            cite = (row.get('Zitierfähige URL') or '').strip()
            if cite:
                cite_urls.add(cite)

    return len(authors), len(set(authors)), len(cite_urls)


def period_distribution_from_metadata(metadata_csv, female_names_file, period=50):
    """Return dict mapping period-start → {female, male, unknown}."""
    female_names = set()
    if os.path.exists(female_names_file):
        with open(female_names_file, "r", encoding="utf-8") as f:
            female_names = {line.strip().lower() for line in f if line.strip()}

    seen = {}
    period_counts = {}

    with open(metadata_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            cite = (row.get('Zitierfähige URL') or '').strip()
            if not cite or cite in seen:
                continue

            pub = (row.get('publikationsdatum') or '').strip()
            author = (row.get('Autor') or '').strip()
            seen[cite] = (pub, author)

    for pub, author in seen.values():
        match = re.search(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", pub)
        if not match:
            continue

        year = int(match.group(0))
        bucket = year - (year % period)

        auth_lower = author.lower()
        if auth_lower in female_names:
            group = "female"
        elif author:
            group = "male"
        else:
            group = "unknown"

        period_counts.setdefault(bucket, {"female": 0, "male": 0, "unknown": 0})
        period_counts[bucket][group] += 1

    return dict(sorted(period_counts.items()))


def list_unique_authors(metadata_csv):
    authors = set()
    with open(metadata_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            autor = (row.get('Autor') or '').strip()
            if autor:
                authors.add(autor)

    print("\nUnique authors:")
    for a in sorted(authors):
        print(" -", a)

    print(f"\nTotal unique authors: {len(authors)}\n")
    return sorted(authors)


def parse_page_count(page_str):
    if not page_str:
        return None

    s = re.sub(r'^[^\d]*', '', page_str.strip())
    s = s.replace('–', '-').replace('—', '-')

    total = 0
    parts = [p.strip() for p in re.split(r'[;,]', s) if p.strip()]

    for part in parts:
        m = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
        if m:
            total += int(m.group(2)) - int(m.group(1)) + 1
        elif re.match(r'^\d+$', part):
            total += 1

    return total or None


def plot_page_length_distribution(metadata_csv, outlier_threshold=30):
    page_lengths = []
    outliers = []

    with open(metadata_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            page_str = (row.get('Pages') or '').strip()
            count = parse_page_count(page_str)
            if count is not None:
                page_lengths.append(count)
                if count > outlier_threshold:
                    outliers.append((row.get('Title', ''), page_str, count))

    if outliers:
        print("\n⚠ OUTLIERS:")
        for t, raw, c in outliers:
            print(f"{c} pages | {raw} | {t}")

    counts = Counter(page_lengths)
    fig, ax = plt.subplots()
    ax.bar(counts.keys(), counts.values())
    ax.set_xlabel("Pages")
    ax.set_ylabel("Reports")
    ax.set_title("Page Length Distribution")
    plt.tight_layout()

    return counts, fig, ax


# ==============================
# MAIN
# ==============================
if __name__ == '__main__':
    print("=" * 60)
    print("REISEBERICHTE DRESDEN — METADATA STATISTICS")
    print("=" * 60)

    rows = count_csv_rows(METADATA_CSV)
    print(f"\nRows in metadata.csv: {rows}")

    folder_count = count_folders(IMAGES_DIR)
    print(f"Folders in images/: {folder_count}")

    total_images = count_total_images(IMAGES_DIR)
    print(f"Total images: {total_images}")

    if folder_count:
        print(f"Average images per folder: {total_images / folder_count:.1f}")

    author_entries, unique_authors, unique_cites = count_authors_and_unique_cite(METADATA_CSV)
    print(f"\nAuthor entries: {author_entries}")
    print(f"Unique authors: {unique_authors}")
    print(f"Unique cite URLs: {unique_cites}")

    periods = period_distribution_from_metadata(METADATA_CSV, "female_names.txt")

    print("\nEntries per 50-year period:")
    for start, g in periods.items():
        print(f"{start}-{start+49}: F:{g['female']} M:{g['male']} U:{g['unknown']}")

    # -----------------------------
    # Plot stacked bar chart
    # -----------------------------
    fig, ax = plt.subplots()

    period_starts = list(periods.keys())
    female_counts = [periods[p]["female"] for p in period_starts]
    male_counts = [periods[p]["male"] for p in period_starts]

    # Compute maximum stacked height
    max_height = max(
        m + f 
        for m, f in zip(male_counts, female_counts)
    )

    # Add 10% headroom
    ax.set_ylim(0, max_height * 1.1)

    # Stack bars
    bar_width = 40  # spans most of the 50-year period

    ax.bar(period_starts, male_counts, width=bar_width, label="Male")
    ax.bar(period_starts, female_counts, width=bar_width,
        bottom=male_counts, label="Female")


    ax.set_title("Number of travelogues per 50-year period")
    ax.set_xlabel("Period start year")
    ax.set_ylabel("Number of reports")
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig("number_of_reports_50.png")
    plt.show()


    list_unique_authors(METADATA_CSV)

    page_counts, fig, ax = plot_page_length_distribution(METADATA_CSV)
    plt.savefig("page_length_distribution.png")
