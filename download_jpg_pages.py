#!/usr/bin/env python3
"""
Download images from a SLUB 'kitodo' jpegs folder given a sample image URL
and a page range.

Example:
    python download_slub_kitodo.py \
        --sample "https://digital.slub-dresden.de/data/kitodo/reisdufrb_281132259_0004/reisdufrb_281132259_0004_tif/jpegs/00000418.tif.original.jpg" \
        --range 410-433 \
        --outdir slub_images \
        --workers 6
"""
import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import requests

REQUEST_TIMEOUT = 30
RETRY_DELAY = 1.0
MAX_RETRIES = 3

def parse_sample_url(sample_url):
    """
    Try to split the sample_url into:
      prefix (up to and including the directory before the numeric filename),
      numeric sample (like '00000418'),
      suffix (like '.tif.original.jpg')
    Returns (prefix, numeric_str, suffix)
    """
    # prefer folder containing 'jpegs/' if present
    m = re.search(r'(.*/jpegs/)(\d+)(\.[^/]+)$', sample_url)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # fallback: last numeric block before the final extension
    m = re.search(r'(.*/)(\d+)(\.[^/]+)$', sample_url)
    if m:
        return m.group(1), m.group(2), m.group(3)

    raise ValueError("Couldn't parse numeric filename from sample URL. "
                     "Provide a sample URL with a numeric filename, e.g. .../jpegs/00000418.tif.original.jpg")

def build_url(prefix, number, width, suffix):
    return f"{prefix}{str(number).zfill(width)}{suffix}"

def download_file(url, outpath):
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            if resp.status_code == 200:
                # write to temporary file then rename
                tmp_path = outpath.with_suffix(outpath.suffix + ".part")
                with open(tmp_path, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                tmp_path.replace(outpath)
                return True, None
            else:
                err = f"HTTP {resp.status_code}"
                # consider 404 final (don't retry too many times), but still retry a few times
        except Exception as e:
            err = str(e)
        attempt += 1
        time.sleep(RETRY_DELAY * attempt)
    return False, err

def parse_range(range_str):
    m = re.match(r'^\s*(\d+)\s*-\s*(\d+)\s*$', range_str)
    if not m:
        raise argparse.ArgumentTypeError("Range must be in the form START-END (e.g. 410-433)")
    a, b = int(m.group(1)), int(m.group(2))
    if a > b:
        raise argparse.ArgumentTypeError("Range start must be <= end")
    return a, b

def main():
    parser = argparse.ArgumentParser(description="Download SLUB kitodo jpegs using a sample URL and a page range.")
    parser.add_argument("--sample", required=True, help="A sample image URL from the same folder (e.g. the first page's jpg URL).")
    parser.add_argument("--range", required=True, help="Page range, e.g. 410-433")
    parser.add_argument("--outdir", default="slub_pages", help="Output folder")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel downloads (default 4)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip files that already exist")
    args = parser.parse_args()

    try:
        start, end = parse_range(args.range)
    except Exception as e:
        print("Bad range:", e)
        sys.exit(1)

    try:
        prefix, sample_num_str, suffix = parse_sample_url(args.sample)
    except ValueError as e:
        print(e)
        sys.exit(1)

    width = len(sample_num_str)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Create list of (page, url, outpath)
    tasks = []
    for page in range(start, end + 1):
        url = build_url(prefix, page, width, suffix)
        # derive local filename same as remote numeric filename + suffix extension
        filename = f"{str(page).zfill(width)}{suffix}"
        outpath = outdir / filename
        tasks.append((page, url, outpath))

    print(f"Detected numeric width = {width}. Downloading {len(tasks)} files to '{outdir}'...\n")

    # use threadpool for parallel downloads
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = {}
        for page, url, outpath in tasks:
            if args.skip_existing and outpath.exists():
                print(f"[{page}] Skipping (exists): {outpath.name}")
                continue
            futures[ex.submit(download_file, url, outpath)] = (page, url, outpath)

        for fut in as_completed(futures):
            page, url, outpath = futures[fut]
            success, err = fut.result()
            if success:
                print(f"[{page}] OK -> {outpath.name}")
            else:
                print(f"[{page}] FAILED ({err}) -> {url}")

    print("\nAll done.")

if __name__ == "__main__":
    main()
