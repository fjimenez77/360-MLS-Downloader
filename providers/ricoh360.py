"""
Provider: Ricoh360 MLS Tours (mls.ricoh360.com)
"""

import re
from urllib.parse import urlparse

PROVIDER_NAME = "ricoh360"
DISPLAY_NAME = "Ricoh360 MLS"
BASE_URL = "https://mls.ricoh360.com"
S3_BASE = "https://{bucket}.s3.{region}.amazonaws.com/{key}"


def detect(url_or_id):
    """Return True if this URL is a Ricoh360 MLS tour."""
    if "ricoh360.com" in url_or_id:
        return True
    # Bare UUID — assume ricoh360 as fallback
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, url_or_id):
        return True
    return False


def extract_ids(url_or_id):
    """Extract tour ID from URL or raw UUID. Returns dict with 'tour_id'."""
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    if re.match(f'^{uuid_pattern}$', url_or_id):
        return {"tour_id": url_or_id}

    parsed = urlparse(url_or_id)
    path_parts = parsed.path.strip('/').split('/')

    for part in path_parts:
        if re.match(f'^{uuid_pattern}$', part):
            return {"tour_id": part}

    raise ValueError(f"Could not extract tour ID from: {url_or_id}")


def fetch_tour_data(session, ids):
    """Fetch tour data. Returns raw JSON."""
    tour_id = ids["tour_id"]

    # Get Next.js build ID
    resp = session.get(BASE_URL + "/")
    resp.raise_for_status()

    build_id = None
    match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
    if match:
        build_id = match.group(1)
    else:
        match = re.search(r'/_next/data/([^/]+)/', resp.text)
        if match:
            build_id = match.group(1)

    if not build_id:
        raise ValueError("Could not extract Next.js build ID from page")

    # Fetch tour JSON
    url = f"{BASE_URL}/_next/data/{build_id}/{tour_id}.json"
    resp = session.get(url, params={"tourId": tour_id})
    resp.raise_for_status()
    return resp.json()


def parse_tour(raw_data):
    """Parse raw API data into normalized tour dict."""
    page_props = raw_data.get("pageProps", {})
    tour_meta = page_props.get("tour", {})
    detail = tour_meta.get("detailData", {}).get("tour", {})

    tour = {
        "id": detail.get("id", ""),
        "provider": PROVIDER_NAME,
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


def image_url(info):
    """Build download URL from S3 info dict."""
    if not info:
        return None
    return S3_BASE.format(
        bucket=info["bucket"],
        region=info["region"],
        key=info["key"],
    )


def preview_url(info):
    """Build preview image URL from S3 info dict."""
    if not info or not info.get("preview_key"):
        return None
    preview = dict(info)
    preview["key"] = preview["preview_key"]
    return image_url(preview)


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
