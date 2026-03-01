#!/usr/bin/env python3
"""
Process reports CSV, combine with links CSV, download images for each report,
organize into folders, and create a full_reports.csv with folder paths and links.
"""
import csv
import os
import re
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 30
RETRY_DELAY = 1.0
MAX_RETRIES = 3

def read_csv(filepath, delimiter=';'):
    """Read CSV file and return list of dicts."""
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            rows.append(row)
    return rows

def write_csv(filepath, fieldnames, rows, delimiter=';'):
    """Write CSV file."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)

def sanitize_folder_name(name):
    """Sanitize folder name by removing/replacing invalid characters."""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces/special with underscore
    name = re.sub(r'\s+', '_', name)
    # Limit length
    name = name[:100]
    return name

def parse_sample_url(sample_url):
    """
    Parse a sample URL to extract prefix, numeric string, and suffix.
    Supports various digital library formats.
    """
    # SLUB kitodo format: .../jpegs/00000418.tif.original.jpg
    m = re.search(r'(.*/jpegs/)(\d+)(\.[^/]+)$', sample_url)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Generic: last numeric block before final extension
    m = re.search(r'(.*/)(\d+)(\.[^/]+)$', sample_url)
    if m:
        return m.group(1), m.group(2), m.group(3)

    return None, None, None

def build_url(prefix, number, width, suffix):
    """Build a URL for a specific page number."""
    return f"{prefix}{str(number).zfill(width)}{suffix}"

def extract_page_numbers(pages_str):
    """
    Extract page numbers from a string like "Seite(n)23-24" or "23-24" or "23, 24".
    Returns list of (start, end) tuples or None if parsing fails.
    """
    if not pages_str or pages_str.strip() == '':
        return None

    # Remove "Seite(n)" prefix if present
    pages_str = re.sub(r'Seite\(n\)', '', pages_str, flags=re.IGNORECASE).strip()
    
    ranges = []
    # Split by comma to handle multiple ranges
    for part in pages_str.split(','):
        part = part.strip()
        # Try range format (e.g., "23-24")
        m = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            ranges.append((start, end))
        # Try single number
        elif re.match(r'^\d+$', part):
            num = int(part)
            ranges.append((num, num))
    
    return ranges if ranges else None

def download_file(url, outpath, skip_existing=True):
    """Download a file with retries."""
    if skip_existing and outpath.exists():
        return True, None

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            if resp.status_code == 200:
                tmp_path = outpath.with_suffix(outpath.suffix + ".part")
                with open(tmp_path, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                tmp_path.replace(outpath)
                return True, None
            else:
                err = f"HTTP {resp.status_code}"
        except Exception as e:
            err = str(e)
        
        attempt += 1
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)
    
    return False, err

def detect_image_format(link):
    """
    Detect the image format from the URL.
    Returns (format_name, is_supported)
    Supported: slub, digitale_sammlungen, archive_org, haab, hab, etc.
    """
    if 'digital.slub-dresden.de' in link:
        return 'slub_kitodo', True
    elif 'digitale-sammlungen.de' in link:
        return 'digitale_sammlungen', True
    elif 'archive.org' in link:
        return 'archive_org', True
    elif 'haab-digital' in link:
        return 'haab', True
    elif 'diglib.hab.de' in link:
        return 'hab', True
    elif 'reise.isgv.de/logs' in link:
        return 'isgv_logs', False  # No JPG available
    else:
        return 'unknown', False

def download_images_for_link(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download images from a specific link for given page ranges.
    Returns list of (page_num, filename, success, error_msg).
    """
    fmt, supported = detect_image_format(link)
    
    if not supported:
        if verbose:
            print(f"  Format '{fmt}' not supported for link: {link}")
        return []

    if fmt == 'slub_kitodo':
        return _download_slub_kitodo(link, pages_ranges, output_dir, workers, verbose)
    elif fmt == 'digitale_sammlungen':
        return _download_digitale_sammlungen(link, pages_ranges, output_dir, workers, verbose)
    elif fmt == 'archive_org':
        return _download_archive_org(link, pages_ranges, output_dir, workers, verbose)
    elif fmt == 'hab':
        return _download_hab(link, pages_ranges, output_dir, workers, verbose)
    elif fmt == 'haab':
        return _download_haab(link, pages_ranges, output_dir, workers, verbose)
    else:
        return []

def _download_slub_kitodo(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download from SLUB kitodo jpegs folder.
    First fetch the page to extract the actual download URL.
    """
    try:
        # Fetch the page to find the download link
        resp = requests.get(link, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for "Einzelseite als Bild herunterladen (JPG)" link
        download_link = None
        for a in soup.find_all('a', href=True):
            if 'JPG' in a.get_text(strip=True) and 'herunterladen' in a.get_text(strip=True).lower():
                download_link = a['href']
                break
        
        if not download_link:
            if verbose:
                print(f"  Could not find JPG download link on {link}")
            return []
        
        # Parse the download URL to extract kitodo base path
        prefix, sample_num_str, suffix = parse_sample_url(download_link)
        if not prefix:
            if verbose:
                print(f"  Could not parse download URL: {download_link}")
            return []
        
    except Exception as e:
        if verbose:
            print(f"  Error fetching page {link}: {e}")
        return []
    
    width = len(sample_num_str) if sample_num_str else 8
    tasks = []
    
    for start, end in pages_ranges:
        for page in range(start, end + 1):
            url = build_url(prefix, page, width, suffix)
            filename = f"{str(page).zfill(width)}{suffix}"
            outpath = Path(output_dir) / filename
            tasks.append((page, url, outpath))
    
    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(download_file, url, outpath): (page, filename) for page, url, outpath in tasks}
        for fut in as_completed(futures):
            page, filename = futures[fut]
            success, err = fut.result()
            results.append((page, filename, success, err))
    
    return results

def _download_digitale_sammlungen(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download from Digitale Sammlungen (BSB).
    Format: https://www.digitale-sammlungen.de/de/view/bsb10467335?page=1048
    Handles comma-separated page parameters (e.g., page=,1 or page=98,99).
    Uses IIIF API to construct image URLs.
    """
    # Extract bsb ID from URL
    m = re.search(r'/(bsb\d+)', link)
    if not m:
        if verbose:
            print(f"  Could not extract BSB ID from: {link}")
        return []
    
    bsb_id = m.group(1)
    
    # Try to extract page parameter from URL to determine offset/padding
    # Format: ?page=98,99 or ?page=,1 (comma-separated values)
    url_page_offset = None
    try:
        from urllib.parse import urlparse, parse_qs
        p = urlparse(link)
        qs = parse_qs(p.query, keep_blank_values=True)
        if 'page' in qs:
            # Get page parameter and split by comma
            page_param = ''.join(qs['page'])  # join in case it's multiple values
            parts = [x.strip() for x in page_param.split(',') if x.strip()]
            if parts:
                # Use the first non-empty page value as offset reference
                url_page_offset = int(parts[0])
    except Exception:
        pass
    
    results = []
    tasks = []
    
    # Use IIIF API to get images
    # Format: https://api.digitale-sammlungen.de/iiif/image/v2/bsb11211065_00098/full/full/0/default.jpg
    for start, end in pages_ranges:
        # Number of pages to download
        num_pages = (end - start) + 1
        
        # Use the URL's page parameter as the actual starting page in the document
        if url_page_offset is not None:
            # Link's page parameter is the actual first page to download
            actual_start = url_page_offset
        else:
            # No page parameter in link; assume CSV page numbers are correct
            actual_start = start
        
        for i, page in enumerate(range(start, end + 1)):
            # Calculate actual image number: url_page_offset + offset within range
            img_number = actual_start + i
            
            # Pad to 5 digits (standard for MDZ/BSB IIIF)
            filename = f"{bsb_id}_{str(img_number).zfill(5)}.jpg"
            url = f"https://api.digitale-sammlungen.de/iiif/image/v2/{bsb_id}_{str(img_number).zfill(5)}/full/full/0/default.jpg"
            outpath = Path(output_dir) / f"{page}.jpg"
            tasks.append((page, url, outpath, filename))
    
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(download_file, url, outpath): (page, filename) for page, url, outpath, filename in tasks}
        for fut in as_completed(futures):
            page, filename = futures[fut]
            success, err = fut.result()
            results.append((page, filename, success, err))
    
    return results

def _download_archive_org(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download from Archive.org.
    Links are like: https://archive.org/details/BriefeEinesAufmerksamenReisendenDieMusikBetreffendBd.21776/page/n107/mode/2up
    Downloads full PDF and full text in addition to individual page images.
    """
    # Extract item ID
    m = re.search(r'/details/([^/]+)/', link)
    if not m:
        return []
    
    item_id = m.group(1)
    results = []
    tasks = []
    
    # Download full PDF
    pdf_url = f"https://archive.org/download/{item_id}/{item_id}.pdf"
    pdf_path = Path(output_dir) / f"{item_id}.pdf"
    tasks.append(("pdf", pdf_url, pdf_path, f"{item_id}.pdf"))
    
    # Download full text
    txt_url = f"https://archive.org/stream/{item_id}/{item_id}_djvu.txt"
    txt_path = Path(output_dir) / f"{item_id}_fulltext.txt"
    tasks.append(("txt", txt_url, txt_path, f"{item_id}_fulltext.txt"))
    
    # Also download individual page images if pages_ranges is provided
    for start, end in pages_ranges:
        for page in range(start, end + 1):
            # Archive.org page image URL
            filename = f"page_{page}.jpg"
            url = f"https://archive.org/download/{item_id}/{item_id}_{str(page).zfill(4)}.jp2"
            outpath = Path(output_dir) / f"{page}.jp2"
            tasks.append((page, url, outpath, filename))
    
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(download_file, url, outpath): (page_id, filename) for page_id, url, outpath, filename in tasks}
        for fut in as_completed(futures):
            page_id, filename = futures[fut]
            success, err = fut.result()
            results.append((page_id, filename, success, err))
    
    return results

def _download_hab(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download from HAB (Herzog August Library).
    Links are like: https://diglib.hab.de/wdb.php?dir=drucke/gm-4947&lang=en
    Use their METS download API.
    """
    # Extract directory from URL
    m = re.search(r'dir=([^&]+)', link)
    if not m:
        if verbose:
            print(f"  Could not extract HAB directory from: {link}")
        return []
    
    hab_dir = m.group(1)
    results = []
    tasks = []
    
    # HAB uses: https://diglib.hab.de/download.php?dir=drucke/gm-4947&page=19
    for start, end in pages_ranges:
        for page in range(start, end + 1):
            filename = f"page_{page}.jpg"
            url = f"https://diglib.hab.de/download.php?dir={hab_dir}&page={page}"
            outpath = Path(output_dir) / f"{page}.jpg"
            tasks.append((page, url, outpath, filename))
    
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(download_file, url, outpath): (page, filename) for page, url, outpath, filename in tasks}
        for fut in as_completed(futures):
            page, filename = futures[fut]
            success, err = fut.result()
            results.append((page, filename, success, err))
    
    return results

def _download_haab(link, pages_ranges, output_dir, workers=4, verbose=False):
    """
    Download from HAAB (Herzogin Anna Amalia Bibliothek).
    Links are like: https://haab-digital.klassik-stiftung.de/viewer/image/1302496816/351/
    Extract the ID and page number to construct download URL.
    """
    # Extract the collection/object ID
    m = re.search(r'/viewer/image/(\d+)/', link)
    if not m:
        if verbose:
            print(f"  Could not extract HAAB ID from: {link}")
        return []
    
    haab_id = m.group(1)
    results = []
    tasks = []
    
    # HAAB IIIF pattern: https://haab-digital.klassik-stiftung.de/iiif/image/v2/{ID}_{PADDED_PAGE}/full/full/0/default.jpg
    for start, end in pages_ranges:
        for page in range(start, end + 1):
            filename = f"{haab_id}_{str(page).zfill(8)}.jpg"
            url = f"https://haab-digital.klassik-stiftung.de/iiif/image/v2/{haab_id}_{str(page).zfill(8)}/full/full/0/default.jpg"
            outpath = Path(output_dir) / f"{page}.jpg"
            tasks.append((page, url, outpath, filename))
    
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(download_file, url, outpath): (page, filename) for page, url, outpath, filename in tasks}
        for fut in as_completed(futures):
            page, filename = futures[fut]
            success, err = fut.result()
            results.append((page, filename, success, err))
    
    return results

def process_reports():
    """Main function to process reports and download images."""
    
    # Read CSV files
    print("Reading Q1731_reports.csv...")
    reports = read_csv('Q1731_reports.csv', delimiter=';')
    
    print("Reading links.csv... (one link per line)")
    # Read links.csv: treat each physical line as one link (do NOT expand comma-separated page params)
    links = []
    with open('links.csv', 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.strip()
            if raw:
                links.append(raw)
    
    if len(links) != len(reports):
        print(f"WARNING: links.csv has {len(links)} links but Q1731_reports.csv has {len(reports)} rows")
    
    # Create output directory
    output_base = Path('images')
    output_base.mkdir(exist_ok=True)
    
    # Process each report
    full_report_rows = []
    
    for i, report in enumerate(reports):
        year = report.get('Year', '').strip()
        title = report.get('Title', '').strip()
        pages_str = report.get('Pages', '').strip()
        
        # Get corresponding link
        link = links[i] if i < len(links) else ''
        
        # Skip if link is isgv logs (no images)
        if 'reise.isgv.de/logs' in link:
            print(f"[{i+1}] Skipping (no images): {title[:50]}")
            continue
        
        # Parse page ranges
        pages_ranges = extract_page_numbers(pages_str)
        if not pages_ranges:
            print(f"[{i+1}] Could not parse pages from '{pages_str}': {title[:50]}")
            continue
        
        # Create folder for this report
        folder_name = f"{i+1:03d}_{year}_{sanitize_folder_name(title)}"
        folder_path = output_base / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        print(f"[{i+1}] Processing: {title[:60]}")
        print(f"     Pages: {pages_str}, Link: {link[:80]}")
        print(f"     Folder: {folder_name}")
        
        # Download images
        results = download_images_for_link(link, pages_ranges, str(folder_path), workers=4, verbose=True)
        
        # Count successes
        successes = sum(1 for _, _, success, _ in results if success)
        print(f"     Downloaded {successes}/{len(results)} files")
        
        # Add to full report
        full_report_rows.append({
            'Index': i + 1,
            'Year': year,
            'Title': title,
            'Pages': pages_str,
            'Link': link,
            'Folder': folder_name,
            'Downloaded': successes
        })
        
        print()
    
    # Write full_reports.csv
    fieldnames = ['Index', 'Year', 'Title', 'Pages', 'Link', 'Folder', 'Downloaded']
    output_csv = 'full_reports.csv'
    write_csv(output_csv, fieldnames, full_report_rows, delimiter=';')
    
    print(f"Saved {len(full_report_rows)} rows to {output_csv}")
    print("Done.")

if __name__ == "__main__":
    try:
        process_reports()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
