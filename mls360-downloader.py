#!/usr/bin/env python3
"""
360 MLS Tour Downloader — CLI
================================
Downloads 360° panoramic images from MLS virtual tour platforms.
Auto-detects provider (Zillow, Ricoh360, etc.) from the URL.

Usage:
    python mls360-downloader.py <url> [--output <dir>] [--enhanced-only] [--originals-only]

Examples:
    python mls360-downloader.py "https://www.zillow.com/homedetails/ADDRESS/ZPID_zpid/"
    python mls360-downloader.py "https://mls.ricoh360.com/TOUR-ID"
    python mls360-downloader.py TOUR-UUID --enhanced-only
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mls360_downloader_core import (
    load_tour,
    download_tour,
    sanitize_filename,
    make_session,
    __version__,
)

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download 360° panoramic images from MLS virtual tours.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported platforms:
  - Zillow 3D Home (zillow.com/homedetails/...)
  - Ricoh360 MLS (mls.ricoh360.com/TOUR-ID)

Examples:
  %(prog)s "https://www.zillow.com/homedetails/ADDRESS/ZPID_zpid/"
  %(prog)s "https://mls.ricoh360.com/TOUR-ID/ROOM-ID"
  %(prog)s TOUR-UUID --enhanced-only
  %(prog)s ZILLOW-URL --output ~/Desktop/my-listing
        """,
    )
    parser.add_argument("url", help="Tour URL (Zillow listing or Ricoh360 tour)")
    parser.add_argument("--output", "-o", help="Output directory (default: ~/Downloads/mls360-<name>)")
    parser.add_argument("--enhanced-only", action="store_true", help="Only download enhanced/8K images")
    parser.add_argument("--originals-only", action="store_true", help="Only download original/4K images")
    parser.add_argument("--json-only", action="store_true", help="Only save tour data JSON, no images")
    parser.add_argument("--version", action="version", version=f"360 MLS Downloader v{__version__}")

    args = parser.parse_args()

    if args.enhanced_only and args.originals_only:
        print("Error: --enhanced-only and --originals-only are mutually exclusive.")
        sys.exit(1)

    print(f"360 MLS Tour Downloader v{__version__}")
    print("=" * 50)

    session = make_session()

    try:
        tour, raw_data, provider = load_tour(args.url, session)
    except ValueError as e:
        print(f"\n  Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  Error fetching tour: {e}")
        sys.exit(1)

    print(f"  Tour: {tour['name']}")
    print(f"  Address: {tour['address']}")
    print(f"  Rooms: {len(tour['rooms'])}")

    enhanced_count = sum(1 for r in tour['rooms'] if r.get('enhanced'))
    if enhanced_count:
        print(f"  Enhanced: {enhanced_count}/{len(tour['rooms'])}")

    if tour.get("listing_photos"):
        print(f"  Listing photos: {len(tour['listing_photos'])}")

    # Set output directory
    if args.output:
        output_dir = args.output
    else:
        dir_name = sanitize_filename(tour['name']) or tour['id'][:12]
        downloads = os.path.join(Path.home(), "Downloads")
        output_dir = os.path.join(downloads, f"mls360-{dir_name}")

    if args.json_only:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        with open(output / "tour-data.json", 'w') as f:
            json.dump(tour, f, indent=2)
        with open(output / "tour-raw.json", 'w') as f:
            json.dump(raw_data, f, indent=2)
        print(f"\n  Saved JSON to: {output.resolve()}")
        return

    # Download
    print(f"\n  Downloading to: {output_dir}")
    print("=" * 50)

    download_tour(
        tour,
        output_dir,
        session=session,
        enhanced_only=args.enhanced_only,
        originals_only=args.originals_only,
    )


if __name__ == "__main__":
    main()
