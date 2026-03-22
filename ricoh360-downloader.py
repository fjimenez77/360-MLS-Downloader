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
import sys
from pathlib import Path

# Import shared core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ricoh360_downloader_core import (
    extract_tour_id,
    get_build_id,
    fetch_tour_data,
    parse_tour,
    download_tour,
    sanitize_filename,
)

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)


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
        output_dir = os.path.join(".", f"ricoh360-{dir_name}")

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
