#!/usr/bin/env python3
"""
360 MLS Tour Downloader — Core Engine
=======================================
Downloads 360° panoramic images from MLS virtual tour platforms.
Supports multiple providers (Zillow, Ricoh360, etc.)
"""

__version__ = "2.0.0"

import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)

# Import provider registry
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from providers import detect_provider


# ── Shared Utilities ────────────────────────────────────────────────────────

def sanitize_filename(name):
    """Make a string safe for use as a filename."""
    return re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '-')


def make_session():
    """Create a requests session with standard headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session


def get_image_url(info):
    """Get download URL from an image info dict (works for all providers).
    Supports both direct URL format (Zillow) and S3 format (Ricoh360).
    """
    if not info:
        return None
    # Direct URL (Zillow and others)
    if "url" in info:
        return info["url"]
    # S3 format (Ricoh360)
    if "bucket" in info:
        return "https://{bucket}.s3.{region}.amazonaws.com/{key}".format(
            bucket=info["bucket"],
            region=info.get("region", "us-west-2"),
            key=info["key"],
        )
    return None


def get_preview_url(room):
    """Get preview/thumbnail URL from a room dict."""
    # Check for dedicated preview field (Zillow)
    if room.get("preview"):
        url = get_image_url(room["preview"])
        if url:
            return url
    # Check for preview_key in original (Ricoh360)
    if room.get("original") and room["original"].get("preview_key"):
        preview_info = dict(room["original"])
        preview_info["key"] = preview_info["preview_key"]
        return get_image_url(preview_info)
    return None


def get_enhanced_preview_url(room):
    """Get enhanced preview URL from a room dict."""
    if room.get("enhanced") and room["enhanced"].get("preview_key"):
        preview_info = dict(room["enhanced"])
        preview_info["key"] = preview_info["preview_key"]
        return get_image_url(preview_info)
    return None


# ── Download Functions ──────────────────────────────────────────────────────

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


def download_tour(tour, output_dir, session=None, enhanced_only=False, originals_only=False):
    """Download all tour assets to disk. Works with any provider."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    if session is None:
        session = make_session()

    # Save tour metadata
    meta_path = output / "tour-data.json"
    with open(meta_path, 'w') as f:
        json.dump(tour, f, indent=2)
    print(f"  Saved tour metadata: {meta_path}")

    # Download brand logo (Ricoh360)
    if tour.get("brand_logo"):
        logo_info = tour["brand_logo"].get("s3") or tour["brand_logo"]
        url = get_image_url(logo_info)
        if url:
            print("\n  Downloading brand logo...")
            download_file(session, url, output / "brand-logo.jpg")

    # Download tripod cover (Ricoh360)
    if tour.get("tripod_cover"):
        cover_info = tour["tripod_cover"].get("s3") or tour["tripod_cover"]
        url = get_image_url(cover_info)
        if url:
            print("  Downloading tripod cover...")
            download_file(session, url, output / "tripod-cover.jpg")

    # Download listing photos (Zillow)
    if tour.get("listing_photos"):
        photos_dir = output / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        photos = tour["listing_photos"]
        print(f"\n  Downloading {len(photos)} listing photos...")
        for i, photo in enumerate(photos):
            url = photo.get("url", "")
            if url:
                ext = "jpg"
                if ".png" in url.lower():
                    ext = "png"
                elif ".webp" in url.lower():
                    ext = "webp"
                caption = sanitize_filename(photo.get("caption", "")) or f"photo"
                filename = f"{i+1:02d}-{caption}.{ext}"
                download_file(session, url, photos_dir / filename)

    # Save listing description (Zillow)
    if tour.get("listing_details"):
        details_path = output / "listing-details.txt"
        details = tour["listing_details"]
        with open(details_path, 'w') as f:
            f.write(f"{'='*60}\n")
            f.write(f"  LISTING DETAILS\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"  Address:     {tour.get('address', '')}\n")
            f.write(f"  Price:       {details.get('price', 'N/A')}\n")
            f.write(f"  Status:      {details.get('status', 'N/A')}\n")
            f.write(f"  Bedrooms:    {details.get('bedrooms', 'N/A')}\n")
            f.write(f"  Bathrooms:   {details.get('bathrooms', 'N/A')}\n")
            f.write(f"  Sq Ft:       {details.get('sqft', 'N/A')}\n")
            f.write(f"  Lot Size:    {details.get('lot_size', 'N/A')}\n")
            f.write(f"  Year Built:  {details.get('year_built', 'N/A')}\n")
            f.write(f"  Home Type:   {details.get('home_type', 'N/A')}\n")
            f.write(f"  MLS #:       {details.get('mls_id', 'N/A')}\n")
            f.write(f"\n{'─'*60}\n  DESCRIPTION\n{'─'*60}\n\n")
            f.write(f"  {details.get('description', 'No description available.')}\n")
            if details.get("facts"):
                f.write(f"\n{'─'*60}\n  PROPERTY FACTS\n{'─'*60}\n\n")
                for fact in details["facts"]:
                    f.write(f"  {fact}\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"  Source: {tour.get('provider', 'unknown')}\n")
            f.write(f"  Generated by 360 MLS Downloader\n")
            f.write(f"{'='*60}\n")
        print(f"  Saved listing details: {details_path}")

    # Download rooms (360° panoramas)
    rooms_dir = output / "rooms"
    total = len(tour["rooms"])

    for room in tour["rooms"]:
        idx = room["index"]
        name = sanitize_filename(room["name"])
        room_dir = rooms_dir / f"{idx:02d}-{name}"
        room_dir.mkdir(parents=True, exist_ok=True)

        status = room.get("enhancement_status", "")
        print(f"\n  [{idx}/{total}] {room['name']}" + (f" ({status})" if status else ""))

        # Original / 4K panorama
        if not enhanced_only and room.get("original"):
            url = get_image_url(room["original"])
            if url:
                ext = "jpg"
                mime = room["original"].get("mime", "image/jpeg")
                if "avif" in mime:
                    ext = "avif"
                elif "png" in mime:
                    ext = "png"
                download_file(session, url, room_dir / f"original.{ext}")

            # Preview
            preview = get_preview_url(room)
            if preview:
                download_file(session, preview, room_dir / "preview.jpg")

        # Enhanced / 8K panorama (optional — some may not be publicly accessible)
        if not originals_only and room.get("enhanced"):
            url = get_image_url(room["enhanced"])
            if url:
                ext = "jpg"
                mime = room["enhanced"].get("mime", "image/jpeg")
                if "avif" in mime:
                    ext = "avif"
                elif "png" in mime:
                    ext = "png"
                if not download_file(session, url, room_dir / f"enhanced.{ext}", retries=1):
                    # 8K may not be available for all panos — not an error
                    pass

            # Enhanced preview
            enh_preview = get_enhanced_preview_url(room)
            if enh_preview:
                download_file(session, enh_preview, room_dir / "enhanced-preview.jpg")

    # Save usage instructions
    _save_instructions(output, tour)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Tour: {tour['name']}")
    print(f"  Address: {tour['address']}")
    print(f"  Provider: {tour.get('provider', 'unknown')}")
    print(f"  Rooms: {total}")
    if tour.get("listing_photos"):
        print(f"  Listing photos: {len(tour['listing_photos'])}")
    print(f"  Saved to: {output.resolve()}")
    print(f"{'='*50}")


# ── Provider-Aware Workflow ─────────────────────────────────────────────────

def load_tour(url_or_id, session=None):
    """Auto-detect provider, fetch, and parse a tour. Returns (tour, raw_data, provider)."""
    if session is None:
        session = make_session()

    provider = detect_provider(url_or_id)
    if not provider:
        raise ValueError(
            f"Unsupported URL: {url_or_id}\n"
            f"Supported platforms: Zillow (zillow.com), Ricoh360 (mls.ricoh360.com)"
        )

    print(f"  Provider: {provider.DISPLAY_NAME}")

    ids = provider.extract_ids(url_or_id)
    print(f"  Fetching tour data...")

    raw_data = provider.fetch_tour_data(session, ids)
    tour = provider.parse_tour(raw_data)

    return tour, raw_data, provider


# ── Instructions ────────────────────────────────────────────────────────────

def _save_instructions(output_dir, tour):
    """Save usage instructions file to the output directory."""
    instructions_path = output_dir / "HOW TO USE THESE IMAGES.txt"
    if instructions_path.exists():
        return

    enhanced_count = sum(1 for r in tour.get("rooms", []) if r.get("enhanced"))
    total = len(tour.get("rooms", []))
    provider = tour.get("provider", "unknown")

    instructions = f"""========================================================
  HOW TO USE YOUR 360° TOUR IMAGES
========================================================

Tour:         {tour.get('name', '')}
Address:      {tour.get('address', '')}
Provider:     {provider}
Rooms:        {total} ({enhanced_count} with enhanced versions)

--------------------------------------------------------
  WHAT'S IN THIS FOLDER
--------------------------------------------------------

rooms/          Each subfolder contains 360° panoramic
                images for one room:
                - original.jpg       Full-res panorama
                - enhanced.jpg/avif  Enhanced version
                - preview.jpg        Smaller thumbnail

photos/         Regular listing photos (if available)

tour-data.json  Complete tour metadata
listing-details.txt  Property details and description

--------------------------------------------------------
  UPLOADING TO REAL ESTATE SITES (Zillow, Realtor, etc.)
--------------------------------------------------------

These images are standard equirectangular JPEG panoramas
— the universal format for 360° photos. Most real estate
platforms auto-detect them as 360° and display them in
their built-in panorama viewer.

TIPS:
  - Use the "enhanced" versions when available
  - Upload rooms in order (01, 02, 03...)
  - The images work as regular photos too on platforms
    that don't support 360°

--------------------------------------------------------
  OFFLINE VIEWING
--------------------------------------------------------

To view these images as an interactive 360° tour:

  1. Use the menu app: python3 mls360-menu.py
     Select option 7: "Build 360° HTML viewer"

  2. Or double-click "Open Tour Viewer.command" (Mac)
     or "Open Tour Viewer.bat" (Windows)

========================================================
  Generated by 360 MLS Downloader
  github.com/fjimenez77/360-MLS-Downloader
========================================================
"""
    with open(instructions_path, "w") as f:
        f.write(instructions)
