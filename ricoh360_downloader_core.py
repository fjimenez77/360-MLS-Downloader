#!/usr/bin/env python3
"""
Ricoh360 MLS Tour Downloader
=============================
Downloads all 360° panoramic images from any Ricoh360 MLS tour URL.

Usage:
    python ricoh360-downloader.py <tour_url> [--output <dir>] [--enhanced-only] [--originals-only]

Examples:
    python ricoh360-downloader.py https://mls.ricoh360.com/f948586f-1c5c-48dc-81fd-6ef9a09a12c0/c84e8d06-2b82-46a0-991a-8814573e048b
    python ricoh360-downloader.py https://mls.ricoh360.com/f948586f-1c5c-48dc-81fd-6ef9a09a12c0 --output ~/Desktop/my-tour
    python ricoh360-downloader.py f948586f-1c5c-48dc-81fd-6ef9a09a12c0 --enhanced-only
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)


S3_BASE = "https://{bucket}.s3.{region}.amazonaws.com/{key}"


def extract_tour_id(url_or_id):
    """Extract tour ID from URL or raw UUID."""
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    if re.match(f'^{uuid_pattern}$', url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)
    path_parts = parsed.path.strip('/').split('/')

    for part in path_parts:
        if re.match(f'^{uuid_pattern}$', part):
            return part

    print(f"Error: Could not extract tour ID from: {url_or_id}")
    sys.exit(1)


def get_build_id(session):
    """Get the Next.js build ID from the main page."""
    resp = session.get("https://mls.ricoh360.com/")
    resp.raise_for_status()

    match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
    if match:
        return match.group(1)

    match = re.search(r'/_next/data/([^/]+)/', resp.text)
    if match:
        return match.group(1)

    print("Error: Could not extract Next.js build ID from page.")
    sys.exit(1)


def fetch_tour_data(session, build_id, tour_id):
    """Fetch the full tour JSON from Next.js data endpoint."""
    url = f"https://mls.ricoh360.com/_next/data/{build_id}/{tour_id}.json"
    params = {"tourId": tour_id}

    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def parse_tour(data):
    """Parse tour data into a clean structure."""
    page_props = data.get("pageProps", {})
    tour_meta = page_props.get("tour", {})
    detail = tour_meta.get("detailData", {}).get("tour", {})

    tour = {
        "id": detail.get("id", ""),
        "name": detail.get("name", ""),
        "address": tour_meta.get("address", ""),
        "description": tour_meta.get("description", ""),
        "photographer": tour_meta.get("username", ""),
        "walkthrough_enabled": detail.get("isWalkthroughEnabled", False),
        "brand_logo": None,
        "tripod_cover": None,
        "thumbnail": None,
        "rooms": [],
    }

    if detail.get("brandLogo"):
        bl = detail["brandLogo"]
        tour["brand_logo"] = {
            "url": bl.get("url", ""),
            "s3": _s3_info(bl.get("picture", {})),
        }

    if detail.get("tripodCover"):
        tc = detail["tripodCover"]
        tour["tripod_cover"] = {
            "size": tc.get("size"),
            "s3": _s3_info(tc.get("picture", {})),
        }

    if tour_meta.get("thumbnail"):
        tour["thumbnail"] = _s3_info(tour_meta["thumbnail"])

    rooms_items = detail.get("rooms", {}).get("items", [])
    for i, rm in enumerate(rooms_items):
        room = {
            "index": i + 1,
            "id": rm.get("id", ""),
            "name": rm.get("name", "Unknown"),
            "enhancement_status": rm.get("enhancementStatus", ""),
            "projection": rm.get("image", {}).get("projectionType", ""),
            "hotspots": rm.get("hotspots", []),
            "original": _s3_info(rm.get("image", {}).get("file", {})),
            "enhanced": None,
        }
        if rm.get("enhancedImage"):
            room["enhanced"] = _s3_info(rm["enhancedImage"].get("file", {}))
        tour["rooms"].append(room)

    return tour


def _s3_info(file_obj):
    """Extract S3 download info from an S3Object."""
    if not file_obj or not file_obj.get("bucket"):
        return None
    return {
        "bucket": file_obj["bucket"],
        "region": file_obj.get("region", "us-west-2"),
        "key": file_obj.get("key", ""),
        "preview_key": file_obj.get("previewKey"),
        "mime": file_obj.get("mimeType", "image/jpeg"),
    }


def s3_url(info):
    """Build a public S3 URL from bucket/region/key."""
    if not info:
        return None
    return S3_BASE.format(
        bucket=info["bucket"],
        region=info["region"],
        key=info["key"],
    )


def sanitize_filename(name):
    """Make a string safe for use as a filename."""
    return re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '-')


def download_file(session, url, dest_path, retries=3):
    """Download a file with retry logic."""
    dest_path = Path(dest_path)
    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"    [skip] Already exists: {dest_path.name}")
        return True

    for attempt in range(retries):
        try:
            resp = session.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_mb = dest_path.stat().st_size / (1024 * 1024)
            print(f"    [ok] {dest_path.name} ({size_mb:.1f} MB)")
            return True

        except Exception as e:
            if attempt < retries - 1:
                print(f"    [retry {attempt+1}] {e}")
                time.sleep(2)
            else:
                print(f"    [FAILED] {dest_path.name}: {e}")
                return False


def download_tour(tour, output_dir, enhanced_only=False, originals_only=False):
    """Download all tour assets to disk."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    # Save tour metadata
    meta_path = output / "tour-data.json"
    with open(meta_path, 'w') as f:
        json.dump(tour, f, indent=2)
    print(f"  Saved tour metadata: {meta_path}")

    # Download brand logo
    if tour["brand_logo"] and tour["brand_logo"]["s3"]:
        url = s3_url(tour["brand_logo"]["s3"])
        if url:
            print("\n  Downloading brand logo...")
            download_file(session, url, output / "brand-logo.jpg")

    # Download tripod cover
    if tour["tripod_cover"] and tour["tripod_cover"]["s3"]:
        url = s3_url(tour["tripod_cover"]["s3"])
        if url:
            print("  Downloading tripod cover...")
            download_file(session, url, output / "tripod-cover.jpg")

    # Download rooms
    rooms_dir = output / "rooms"
    total = len(tour["rooms"])

    for room in tour["rooms"]:
        idx = room["index"]
        name = sanitize_filename(room["name"])
        room_dir = rooms_dir / f"{idx:02d}-{name}"
        room_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  [{idx}/{total}] {room['name']} ({room['enhancement_status']})")

        # Original
        if not enhanced_only and room["original"]:
            url = s3_url(room["original"])
            if url:
                download_file(session, url, room_dir / "original.jpg")

            # Preview (smaller version)
            if room["original"].get("preview_key"):
                preview_info = dict(room["original"])
                preview_info["key"] = preview_info["preview_key"]
                url = s3_url(preview_info)
                if url:
                    download_file(session, url, room_dir / "preview.jpg")

        # Enhanced
        if not originals_only and room["enhanced"]:
            url = s3_url(room["enhanced"])
            if url:
                download_file(session, url, room_dir / "enhanced.jpg")

            if room["enhanced"].get("preview_key"):
                preview_info = dict(room["enhanced"])
                preview_info["key"] = preview_info["preview_key"]
                url = s3_url(preview_info)
                if url:
                    download_file(session, url, room_dir / "enhanced-preview.jpg")

    # Summary
    print(f"\n{'='*50}")
    print(f"  Tour: {tour['name']}")
    print(f"  Address: {tour['address']}")
    print(f"  Photographer: {tour['photographer']}")
    print(f"  Rooms: {total}")
    print(f"  Saved to: {output.resolve()}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="Download Ricoh360 MLS virtual tours — all 360° panoramic images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://mls.ricoh360.com/TOUR-ID/ROOM-ID
  %(prog)s https://mls.ricoh360.com/TOUR-ID --output ~/tours/my-house
  %(prog)s TOUR-UUID --enhanced-only
  %(prog)s TOUR-URL --originals-only
        """,
    )
    parser.add_argument("url", help="Ricoh360 tour URL or tour UUID")
    parser.add_argument("--output", "-o", help="Output directory (default: ./<tour-name>)")
    parser.add_argument("--enhanced-only", action="store_true", help="Only download enhanced images")
    parser.add_argument("--originals-only", action="store_true", help="Only download original images")
    parser.add_argument("--json-only", action="store_true", help="Only save tour data JSON, no images")

    args = parser.parse_args()

    if args.enhanced_only and args.originals_only:
        print("Error: --enhanced-only and --originals-only are mutually exclusive.")
        sys.exit(1)

    print("Ricoh360 Tour Downloader")
    print("=" * 50)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    # Step 1: Extract tour ID
    tour_id = extract_tour_id(args.url)
    print(f"  Tour ID: {tour_id}")

    # Step 2: Get Next.js build ID
    print("  Fetching build ID...")
    build_id = get_build_id(session)
    print(f"  Build ID: {build_id}")

    # Step 3: Fetch tour data
    print("  Fetching tour data...")
    raw_data = fetch_tour_data(session, build_id, tour_id)

    # Step 4: Parse
    tour = parse_tour(raw_data)
    print(f"  Tour: {tour['name']}")
    print(f"  Address: {tour['address']}")
    print(f"  Photographer: {tour['photographer']}")
    print(f"  Rooms: {len(tour['rooms'])}")

    enhanced_count = sum(1 for r in tour['rooms'] if r['enhanced'])
    print(f"  Enhanced: {enhanced_count}/{len(tour['rooms'])}")

    # Step 5: Set output directory
    if args.output:
        output_dir = args.output
    else:
        dir_name = sanitize_filename(tour['name']) or tour_id
        downloads = os.path.join(Path.home(), "Downloads")
        output_dir = os.path.join(downloads, f"ricoh360-{dir_name}")

    if args.json_only:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        with open(output / "tour-data.json", 'w') as f:
            json.dump(tour, f, indent=2)
        with open(output / "tour-raw.json", 'w') as f:
            json.dump(raw_data, f, indent=2)
        print(f"\n  Saved JSON to: {output.resolve()}")
        return

    # Step 6: Download
    print(f"\n  Downloading to: {output_dir}")
    print("=" * 50)

    download_tour(
        tour,
        output_dir,
        enhanced_only=args.enhanced_only,
        originals_only=args.originals_only,
    )


if __name__ == "__main__":
    main()
