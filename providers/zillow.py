"""
Provider: Zillow 3D Home Tours + Listing Data (zillow.com)
Extracts 360° panoramas, listing photos, property details, and description.
"""

import json
import re

PROVIDER_NAME = "zillow"
DISPLAY_NAME = "Zillow 3D Home"
CDN_BASE = "https://www.zillowstatic.com/vrmodels/"


def detect(url_or_id):
    """Return True if this URL is a Zillow listing."""
    return "zillow.com" in url_or_id


def extract_ids(url_or_id):
    """Return the listing URL for later fetching."""
    return {"listing_url": url_or_id}


def fetch_tour_data(session, ids):
    """Fetch Zillow tour data using interactive browser (user solves any CAPTCHA)."""
    listing_url = ids["listing_url"]

    html = _fetch_page_interactive(listing_url)

    # Extract the embedded JSON data from the page
    page_data = _extract_page_data(html)

    # Normalize escaped quotes for searching
    html_norm = html.replace('\\"', '"').replace("\\'", "'")

    # Extract vrModelGuid for 3D tour
    vr_model_guid = None
    revision_id = None

    vr_match = re.search(r'"vrModelGuid"\s*:\s*"([0-9a-f\-]{36})"', html_norm)
    if vr_match:
        vr_model_guid = vr_match.group(1)

        # Find IMX manifest revision
        imx_match = re.search(
            r'vrmodels/' + re.escape(vr_model_guid) + r'/imx_([a-z0-9]+)\.json', html_norm
        )
        if imx_match:
            revision_id = imx_match.group(1)
        else:
            imx_match2 = re.search(r'imx_([a-z0-9]{8,12})\.json', html_norm)
            if imx_match2:
                revision_id = imx_match2.group(1)

    # Fetch IMX manifest if available
    manifest = {}
    if vr_model_guid and revision_id:
        manifest_url = f"{CDN_BASE}{vr_model_guid}/imx_{revision_id}.json"
        try:
            resp = session.get(manifest_url)
            resp.raise_for_status()
            manifest = resp.json()
        except Exception:
            pass  # Tour may not exist, continue with listing data

    # Combine everything
    manifest["_page_data"] = page_data
    manifest["_listing_url"] = listing_url
    manifest["_has_3d_tour"] = bool(vr_model_guid and revision_id and manifest.get("panos"))

    return manifest


def parse_tour(raw_data):
    """Parse into normalized tour dict with listing data."""
    page_data = raw_data.get("_page_data", {})
    panos = raw_data.get("panos", {})
    vr_model_guid = raw_data.get("vrModelGuid", "")
    has_3d = raw_data.get("_has_3d_tour", False)

    # Extract address
    address = _get_address(page_data)
    tour_name = address.split(",")[0] if address else vr_model_guid[:12] if vr_model_guid else "Zillow Listing"

    # Extract listing details
    listing_details = _get_listing_details(page_data)

    # Extract listing photos
    listing_photos = _get_listing_photos(page_data)

    tour = {
        "id": vr_model_guid or page_data.get("zpid", ""),
        "provider": PROVIDER_NAME,
        "name": tour_name,
        "address": address,
        "description": listing_details.get("description", ""),
        "photographer": "Zillow 3D Home",
        "walkthrough_enabled": has_3d,
        "brand_logo": None,
        "tripod_cover": None,
        "thumbnail": None,
        "rooms": [],
        "listing_photos": listing_photos,
        "listing_details": listing_details,
    }

    # Parse 360° panoramas if available
    if has_3d:
        sorted_panos = sorted(panos.items(), key=lambda x: x[1].get("order", 0))

        for i, (pano_id, pano) in enumerate(sorted_panos):
            tk = pano.get("textureKeys", {})
            path_prefix = tk.get("pathPrefix", "")

            original_url = f"{CDN_BASE}{path_prefix}{tk.get('4k', 'panorama_4k.jpg')}"
            preview_url_str = f"{CDN_BASE}{path_prefix}{tk.get('thumbnail', 'thumbnail.jpg')}"

            enhanced_url = None
            if tk.get("8k"):
                enhanced_url = f"{CDN_BASE}{path_prefix}{tk['8k']}"

            room = {
                "index": i + 1,
                "id": pano_id,
                "name": pano.get("title", f"Room {i + 1}"),
                "enhancement_status": "COMPLETED",
                "projection": "equirectangular",
                "hotspots": pano.get("exits", []),
                "original": {
                    "url": original_url,
                    "mime": "image/jpeg",
                },
                "enhanced": {
                    "url": enhanced_url,
                    "mime": "image/avif",
                } if enhanced_url else None,
                "preview": {
                    "url": preview_url_str,
                },
            }
            tour["rooms"].append(room)

    return tour


# ── Page Data Extraction ────────────────────────────────────────────────────

def _extract_page_data(html):
    """Extract structured data from Zillow listing page HTML."""
    data = {}

    # Normalize escaped quotes for easier regex matching
    # Zillow embeds JSON inside script tags with escaped quotes (\")
    html_norm = html.replace('\\"', '"').replace("\\'", "'")

    # Try to find the main JSON-LD structured data
    ld_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    if ld_match:
        try:
            ld_data = json.loads(ld_match.group(1))
            if isinstance(ld_data, list):
                for item in ld_data:
                    if item.get("@type") in ("SingleFamilyResidence", "Apartment", "House", "Residence"):
                        data["ld"] = item
                        break
                if "ld" not in data and ld_data:
                    data["ld"] = ld_data[0]
            else:
                data["ld"] = ld_data
        except (json.JSONDecodeError, TypeError):
            pass

    # Use normalized HTML (escaped quotes resolved) for all regex
    h = html_norm

    # Extract zpid
    zpid_match = re.search(r'"zpid"\s*:\s*["\']?(\d+)', h)
    if zpid_match:
        data["zpid"] = zpid_match.group(1)

    # Price
    price_match = re.search(r'"price"\s*:\s*(\d+)', h)
    if price_match:
        data["price"] = int(price_match.group(1))

    # Bedrooms/Bathrooms
    bed_match = re.search(r'"bedrooms"\s*:\s*(\d+)', h)
    if not bed_match:
        bed_match = re.search(r'zillow_fb:beds"\s+content="(\d+)"', html)
    if bed_match:
        data["bedrooms"] = int(bed_match.group(1))

    bath_match = re.search(r'"bathrooms"\s*:\s*(\d+\.?\d*)', h)
    if not bath_match:
        bath_match = re.search(r'zillow_fb:baths"\s+content="(\d+\.?\d*)"', html)
    if bath_match:
        data["bathrooms"] = float(bath_match.group(1))

    # Square footage
    sqft_match = re.search(r'"livingArea"\s*:\s*"?([\d,]+)\s*(?:sqft|sq)', h)
    if not sqft_match:
        sqft_match = re.search(r'"livingArea"\s*:\s*(\d+)', h)
    if sqft_match:
        data["sqft"] = int(sqft_match.group(1).replace(",", ""))

    # Lot size
    lot_match = re.search(r'"lotSize"\s*:\s*"?([\d,]+)\s*(?:sqft|sq)', h)
    if not lot_match:
        lot_match = re.search(r'"lotSize"\s*:\s*(\d+)', h)
    if lot_match:
        data["lot_size"] = int(lot_match.group(1).replace(",", ""))

    # Year built
    year_match = re.search(r'"yearBuilt"\s*:\s*(\d{4})', h)
    if year_match:
        data["year_built"] = int(year_match.group(1))

    # Home type
    type_match = re.search(r'"homeType"\s*:\s*"([^"]+)"', h)
    if type_match:
        data["home_type"] = type_match.group(1)

    # Description — find the listing-specific description (not meta/search page blurb)
    # The real description is typically longer and near other listing fields
    desc_candidates = re.findall(r'"description"\s*:\s*"((?:[^"\\]|\\.){50,})"', h)
    best_desc = None
    for candidate in desc_candidates:
        # Skip generic Zillow search blurbs
        if "has" in candidate and "homes for sale" in candidate:
            continue
        if "View listing photos" in candidate:
            continue
        if "detailed real estate filters" in candidate:
            continue
        best_desc = candidate
        break
    if best_desc:
        try:
            data["description"] = best_desc.encode().decode('unicode_escape')
        except Exception:
            data["description"] = best_desc

    # Address components
    for field in ("streetAddress", "city", "state", "zipcode"):
        m = re.search(rf'"{field}"\s*:\s*"([^"]+)"', h)
        if m:
            data[field] = m.group(1)

    # Home status
    status_match = re.search(r'"homeStatus"\s*:\s*"([^"]+)"', h)
    if status_match:
        data["status"] = status_match.group(1)

    # MLS ID
    mls_match = re.search(r'"mlsId"\s*:\s*"([^"]+)"', h)
    if mls_match:
        data["mls_id"] = mls_match.group(1)

    # ── Extended Property Facts ──────────────────────────────────────

    # Array-valued facts
    array_facts = {
        "heating": "heating",
        "cooling": "cooling",
        "appliances": "appliances",
        "flooring": "flooring",
        "constructionMaterials": "construction_materials",
        "fireplaceFeatures": "fireplace_features",
        "poolFeatures": "pool_features",
        "parkingFeatures": "parking_features",
        "laundryFeatures": "laundry_features",
        "windowFeatures": "window_features",
        "patioAndPorchFeatures": "patio_features",
        "exteriorFeatures": "exterior_features",
        "securityFeatures": "security_features",
        "communityFeatures": "community_features",
        "lotFeatures": "lot_features",
        "waterSource": "water_source",
        "sewer": "sewer",
        "electric": "electric",
    }
    for json_key, data_key in array_facts.items():
        m = re.search(rf'"{json_key}"\s*:\s*(\[[^\]]*\])', h)
        if m:
            try:
                val = json.loads(m.group(1))
                # Filter out "None", "N/A", null values
                val = [x for x in val if x and x not in ("None", "N/A", "null", None)]
                if val:
                    data[data_key] = val
            except (json.JSONDecodeError, TypeError):
                pass

    # Scalar facts
    scalar_facts = {
        "fireplaces": ("fireplaces", int),
        "stories": ("stories", int),
        "roofType": ("roof_type", str),
        "propertyCondition": ("property_condition", str),
        "builderName": ("builder_name", str),
        "parcelNumber": ("parcel_number", str),
        "propertySubType": ("property_subtype", str),  # Note: may be array — handled below
        "garageSpaces": ("garage_spaces", int),
        "totalParkingSpaces": ("total_parking", int),
        "lotSizeDimensions": ("lot_dimensions", str),
    }
    for json_key, (data_key, conv) in scalar_facts.items():
        m = re.search(rf'"{json_key}"\s*:\s*"([^"]+)"', h)
        if not m:
            # Try unquoted numeric value
            m = re.search(rf'"{json_key}"\s*:\s*(\d+)', h)
        if m:
            val = m.group(1).strip()
            if val and val != "null":
                try:
                    data[data_key] = conv(val)
                except (ValueError, TypeError):
                    data[data_key] = val

    # Rooms with dimensions
    rooms_data = []
    # Extract from rendered HTML spans (more reliable)
    room_sections = re.findall(
        r'(?:Bedroom|Bathroom|Kitchen|Living|Dining|Office|Family|Primary|Laundry|Garage|Game|Utility|Bonus)'
        r'[^<]*?(?:Area|Dimensions|Features)[^<]*',
        h, re.IGNORECASE
    )

    # Try the JSON rooms array
    rooms_match = re.search(r'"rooms"\s*:\s*\[((?:\{[^}]*\},?\s*)*)\]', h)
    if rooms_match:
        try:
            rooms_json = json.loads("[" + rooms_match.group(1) + "]")
            for rm in rooms_json:
                room_type = rm.get("roomType", "")
                room_area = rm.get("roomArea", "")
                room_dims = rm.get("roomDimensions", "")
                room_features = rm.get("features", "")
                room_level = rm.get("level", "")
                if room_type:
                    rooms_data.append({
                        "type": room_type,
                        "area": room_area,
                        "dimensions": room_dims,
                        "features": room_features,
                        "level": room_level,
                    })
        except (json.JSONDecodeError, TypeError):
            pass
    if rooms_data:
        data["rooms_detail"] = rooms_data

    # HOA
    hoa_match = re.search(r'"associationFee"\s*:\s*"?(\d+)"?', h)
    if hoa_match:
        data["hoa_fee"] = int(hoa_match.group(1))
    hoa_freq = re.search(r'"associationFeeFrequency"\s*:\s*"([^"]+)"', h)
    if hoa_freq:
        data["hoa_frequency"] = hoa_freq.group(1)
    hoa_name = re.search(r'"associationName"\s*:\s*"([^"]+)"', h)
    if hoa_name and hoa_name.group(1) != "null":
        data["hoa_name"] = hoa_name.group(1)

    # Listing agent
    agent_match = re.search(r'"attributionInfo"\s*:\s*\{[^}]*"agentName"\s*:\s*"([^"]+)"', h)
    if agent_match:
        data["agent_name"] = agent_match.group(1)
    broker_match = re.search(r'"brokerName"\s*:\s*"([^"]+)"', h)
    if broker_match:
        data["broker_name"] = broker_match.group(1)
    agent_phone = re.search(r'"agentPhoneNumber"\s*:\s*"([^"]+)"', h)
    if agent_phone:
        data["agent_phone"] = agent_phone.group(1)

    # Subdivision
    subdiv_match = re.search(r'"subdivisionName"\s*:\s*"([^"]+)"', h)
    if subdiv_match:
        data["subdivision"] = subdiv_match.group(1)

    # Photos — use normalized HTML for URL extraction
    photo_urls = []
    photo_pattern = re.findall(r'"url"\s*:\s*"(https://photos\.zillowstatic\.com/[^"]+)"', h)
    seen = set()
    for url in photo_pattern:
        # Get the highest resolution version
        if "uncropped_scaled_within_1536_1152" in url or "uncropped_scaled_within_1344_1008" in url:
            # Normalize to dedupe
            base = re.sub(r'_\d+_\d+\.', '_NORM.', url)
            if base not in seen:
                seen.add(base)
                photo_urls.append(url)

    # If no high-res found, try any photo URL
    if not photo_urls:
        for url in photo_pattern:
            if url not in seen and "p_f" not in url:
                seen.add(url)
                photo_urls.append(url)
                if len(photo_urls) >= 50:
                    break

    data["photo_urls"] = photo_urls

    # ── DOM-based fact extraction (rendered text after "Show more" click) ──
    # This catches data that isn't in the JSON blobs but IS in the rendered DOM
    _extract_dom_facts(html, data)

    return data


def _extract_dom_facts(html, data):
    """Extract facts from rendered DOM text (visible after 'Show more' click).
    Only fills in keys that are missing — doesn't overwrite JSON-sourced data."""

    # Strip HTML tags to get plain text
    text = re.sub(r'<[^>]+>', '\n', html)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Helper: extract bullet values after a heading
    def _extract_section_items(heading_pattern):
        m = re.search(heading_pattern + r'(.*?)(?=\n\s*(?:[A-Z][a-z]+ ?(?:&amp;|&) |[A-Z][a-z]+\n|$))', text, re.DOTALL | re.IGNORECASE)
        if not m:
            return []
        section = m.group(1) if m.lastindex else m.group(0)
        items = []
        for line in section.split('\n'):
            line = line.strip().lstrip('•').lstrip('·').strip()
            if line and len(line) > 2 and not line.startswith('Show'):
                items.append(line)
        return items

    # Helper: extract "Key: Value" pairs from bullet items
    def _parse_kv_items(items):
        result = {}
        for item in items:
            if ':' in item:
                k, v = item.split(':', 1)
                result[k.strip()] = v.strip()
            else:
                result[item] = ""
        return result

    # ── Heating ──
    if "heating" not in data:
        m = re.search(r'Heating\s*\n+\s*(?:•\s*)?([^\n]+)', text)
        if m:
            val = m.group(1).strip().lstrip('•').strip()
            if val and val not in ('None', 'N/A'):
                data["heating"] = [x.strip() for x in val.split(',')]

    # ── Cooling ──
    if "cooling" not in data:
        m = re.search(r'Cooling\s*\n+\s*(?:•\s*)?([^\n]+)', text)
        if m:
            val = m.group(1).strip().lstrip('•').strip()
            if val and val not in ('None', 'N/A'):
                data["cooling"] = [x.strip() for x in val.split(',')]

    # ── Appliances ──
    if "appliances" not in data:
        m = re.search(r'Appliances\s*\n+\s*(?:•\s*)?Included:\s*([^\n]+)', text)
        if m:
            data["appliances"] = [x.strip() for x in m.group(1).split(',')]

    # ── Laundry ──
    if "laundry_features" not in data:
        m = re.search(r'(?:•\s*)?Laundry:\s*([^\n]+)', text)
        if m:
            data["laundry_features"] = [x.strip() for x in m.group(1).split(',')]

    # ── Flooring ──
    if "flooring" not in data:
        m = re.search(r'(?:•\s*)?Flooring:\s*([^\n]+)', text)
        if m:
            data["flooring"] = [x.strip() for x in m.group(1).split(',')]

    # ── Windows ──
    if "window_features" not in data:
        m = re.search(r'(?:•\s*)?Windows:\s*([^\n]+)', text)
        if m:
            data["window_features"] = [x.strip() for x in m.group(1).split(',')]

    # ── Interior features (the big list) ──
    if "interior_features" not in data:
        m = re.search(r'Features\s*\n+\s*(?:•\s*)?([A-Z][^\n]{20,})', text)
        if m:
            val = m.group(1).strip()
            if 'Living Area' in val or 'Floorplan' in val or 'Kitchen' in val:
                data["interior_features"] = [x.strip() for x in val.split(',')]

    # ── Fireplace ──
    if "fireplaces" not in data:
        m = re.search(r'(?:•\s*)?Has fireplace:\s*(\w+)', text)
        if m:
            data["has_fireplace"] = m.group(1)
        m2 = re.search(r'(?:•\s*)?Fireplace features:\s*([^\n]+)', text)
        if m2:
            data["fireplace_features"] = [x.strip() for x in m2.group(1).split(',')]

    # ── Basement ──
    m = re.search(r'(?:•\s*)?Has basement:\s*(\w+)', text)
    if m:
        data["has_basement"] = m.group(1)

    # ── Exterior features ──
    if "exterior_features" not in data:
        m = re.search(r'(?:•\s*)?Exterior features:\s*([^\n]+)', text)
        if m:
            data["exterior_features"] = [x.strip() for x in m.group(1).split(',')]

    # ── Patio/Porch ──
    if "patio_features" not in data:
        m = re.search(r'(?:•\s*)?Patio\s*(?:&|&amp;)\s*porch:\s*([^\n]+)', text)
        if m:
            data["patio_features"] = [x.strip() for x in m.group(1).split(',')]

    # ── Fencing ──
    if "fencing" not in data:
        m = re.search(r'(?:•\s*)?Fencing:\s*([^\n]+)', text)
        if m:
            data["fencing"] = m.group(1).strip()

    # ── Pool ──
    if "pool_features" not in data:
        m = re.search(r'(?:•\s*)?Pool features:\s*([^\n]+)', text)
        if m:
            val = m.group(1).strip()
            if val != 'None':
                data["pool_features"] = [x.strip() for x in val.split(',')]

    # ── Levels/Stories ──
    if "stories" not in data:
        m = re.search(r'(?:•\s*)?Stories:\s*(\d+)', text)
        if m:
            data["stories"] = int(m.group(1))
        m2 = re.search(r'(?:•\s*)?Levels:\s*([^\n]+)', text)
        if m2:
            data["levels"] = m2.group(1).strip()

    # ── Construction materials ──
    if "construction_materials" not in data:
        # Look under Materials heading
        m = re.search(r'Materials\s*\n+\s*(?:•\s*)?([^\n]+)', text)
        if m:
            val = m.group(1).strip()
            if val and not val.startswith('Foundation'):
                data["construction_materials"] = [x.strip() for x in val.split(',')]

    # ── Foundation ──
    if "foundation" not in data:
        m = re.search(r'(?:•\s*)?Foundation:\s*([^\n]+)', text)
        if m:
            data["foundation"] = m.group(1).strip()

    # ── Roof ──
    if "roof_type" not in data:
        m = re.search(r'(?:•\s*)?Roof:\s*([^\n]+)', text)
        if m:
            data["roof_type"] = m.group(1).strip()

    # ── Architectural style ──
    if "architectural_style" not in data:
        m = re.search(r'(?:•\s*)?Architectural style:\s*([^\n]+)', text)
        if m:
            data["architectural_style"] = m.group(1).strip()

    # ── Condition ──
    if "property_condition" not in data:
        m = re.search(r'Condition\s*\n+\s*(?:•\s*)?([^\n]+)', text)
        if m:
            data["property_condition"] = m.group(1).strip()

    # ── Sewer ──
    if "sewer" not in data:
        m = re.search(r'(?:•\s*)?Sewer:\s*([^\n]+)', text)
        if m:
            data["sewer"] = [x.strip() for x in m.group(1).split(',')]

    # ── Water ──
    if "water_source" not in data:
        m = re.search(r'(?:•\s*)?Water:\s*([^\n]+)', text)
        if m:
            data["water_source"] = [x.strip() for x in m.group(1).split(',')]

    # ── Utilities ──
    if "utilities" not in data:
        m = re.search(r'(?:•\s*)?Utilities for property:\s*([^\n]+)', text)
        if m:
            data["utilities"] = [x.strip() for x in m.group(1).split(',')]

    # ── Security ──
    if "security_features" not in data:
        m = re.search(r'(?:•\s*)?Security:\s*([^\n]+)', text)
        if m:
            data["security_features"] = [x.strip() for x in m.group(1).split(',')]

    # ── Community features ──
    if "community_features" not in data:
        m = re.search(r'Community\s*\n+\s*(?:•\s*)?Features:\s*([^\n]+)', text)
        if m:
            data["community_features"] = [x.strip() for x in m.group(1).split(',') if x.strip() not in ('None', 'N/A')]

    # ── Subdivision ──
    if "subdivision" not in data:
        m = re.search(r'(?:•\s*)?Subdivision:\s*([^\n]+)', text)
        if m:
            data["subdivision"] = m.group(1).strip()

    # ── Region ──
    if "region" not in data:
        m = re.search(r'(?:•\s*)?Region:\s*([^\n]+)', text)
        if m:
            data["region"] = m.group(1).strip()

    # ── Parcel number ──
    if "parcel_number" not in data:
        m = re.search(r'(?:•\s*)?Parcel number:\s*([^\n]+)', text)
        if m:
            data["parcel_number"] = m.group(1).strip()

    # ── Rooms from DOM (if JSON rooms empty) ──
    if "rooms_detail" not in data or not data["rooms_detail"]:
        rooms = []
        # Pattern: "Primary bedroom\nFeatures: ...\nArea: ...\nDimensions: ..."
        room_patterns = re.finditer(
            r'(Primary bedroom|Primary bathroom|Bedroom \d+|Bathroom \d+|Kitchen|Living room|'
            r'Dining room|Family room|Office|Laundry|Garage|Game room|Bonus room|Utility room)\s*\n'
            r'((?:\s*(?:•\s*)?(?:Features|Area|Dimensions|Level):[^\n]+\n?)*)',
            text, re.IGNORECASE
        )
        for rm in room_patterns:
            room_info = {"type": rm.group(1).strip()}
            details = rm.group(2)
            feat = re.search(r'Features:\s*([^\n]+)', details)
            area = re.search(r'Area:\s*(\d+)', details)
            dims = re.search(r'Dimensions:\s*([^\n]+)', details)
            if feat:
                room_info["features"] = feat.group(1).strip()
            if area:
                room_info["area"] = area.group(1).strip()
            if dims:
                room_info["dimensions"] = dims.group(1).strip()
            rooms.append(room_info)
        if rooms:
            data["rooms_detail"] = rooms


def _get_address(page_data):
    """Build address string from page data."""
    parts = []
    if page_data.get("streetAddress"):
        parts.append(page_data["streetAddress"])
    if page_data.get("city"):
        parts.append(page_data["city"])
    if page_data.get("state"):
        parts.append(page_data["state"])
    if page_data.get("zipcode"):
        parts.append(page_data["zipcode"])
    return ", ".join(parts) if parts else ""


def _get_listing_details(page_data):
    """Build listing details dict."""
    def fmt_price(p):
        if not p:
            return "N/A"
        return f"${p:,}"

    def fmt_sqft(s):
        if not s:
            return "N/A"
        return f"{s:,} sq ft"

    def fmt_list(lst):
        if not lst:
            return None
        return ", ".join(str(x) for x in lst)

    details = {
        "price": fmt_price(page_data.get("price")),
        "status": page_data.get("status", "N/A"),
        "bedrooms": str(page_data.get("bedrooms", "N/A")),
        "bathrooms": str(page_data.get("bathrooms", "N/A")),
        "sqft": fmt_sqft(page_data.get("sqft")),
        "lot_size": fmt_sqft(page_data.get("lot_size")),
        "lot_dimensions": page_data.get("lot_dimensions", ""),
        "lot_features": fmt_list(page_data.get("lot_features")),
        "year_built": str(page_data.get("year_built", "N/A")),
        "home_type": page_data.get("home_type", "N/A"),
        "property_subtype": page_data.get("property_subtype", ""),
        "property_condition": page_data.get("property_condition", ""),
        "stories": page_data.get("stories", ""),
        "mls_id": page_data.get("mls_id", "N/A"),
        "parcel_number": page_data.get("parcel_number", ""),
        "description": page_data.get("description", "No description available."),
        # Interior
        "heating": fmt_list(page_data.get("heating")),
        "cooling": fmt_list(page_data.get("cooling")),
        "appliances": fmt_list(page_data.get("appliances")),
        "flooring": fmt_list(page_data.get("flooring")),
        "laundry": fmt_list(page_data.get("laundry_features")),
        "windows": fmt_list(page_data.get("window_features")),
        "fireplaces": page_data.get("fireplaces", ""),
        "fireplace_features": fmt_list(page_data.get("fireplace_features")),
        # Exterior
        "construction_materials": fmt_list(page_data.get("construction_materials")),
        "roof": page_data.get("roof_type", ""),
        "parking": fmt_list(page_data.get("parking_features")),
        "total_parking": page_data.get("total_parking", ""),
        "garage_spaces": page_data.get("garage_spaces", ""),
        "patio": fmt_list(page_data.get("patio_features")),
        "exterior": fmt_list(page_data.get("exterior_features")),
        "pool": fmt_list(page_data.get("pool_features")),
        "fencing": page_data.get("fencing", "") if isinstance(page_data.get("fencing"), str) else fmt_list(page_data.get("fencing")),
        # Interior features
        "interior_features": fmt_list(page_data.get("interior_features")),
        "has_basement": page_data.get("has_basement", ""),
        "has_fireplace": page_data.get("has_fireplace", ""),
        # Construction
        "builder": page_data.get("builder_name", ""),
        "foundation": page_data.get("foundation", ""),
        "architectural_style": page_data.get("architectural_style", ""),
        # Utilities
        "electric": fmt_list(page_data.get("electric")),
        "water": fmt_list(page_data.get("water_source")),
        "sewer": fmt_list(page_data.get("sewer")),
        "utilities": fmt_list(page_data.get("utilities")),
        "levels": page_data.get("levels", ""),
        "region": page_data.get("region", ""),
        # Community
        "security": fmt_list(page_data.get("security_features")),
        "community": fmt_list(page_data.get("community_features")),
        "subdivision": page_data.get("subdivision", ""),
        # HOA
        "hoa_fee": page_data.get("hoa_fee", ""),
        "hoa_frequency": page_data.get("hoa_frequency", ""),
        "hoa_name": page_data.get("hoa_name", ""),
        # Agent
        "agent_name": page_data.get("agent_name", ""),
        "agent_phone": page_data.get("agent_phone", ""),
        "broker_name": page_data.get("broker_name", ""),
        # Rooms detail
        "rooms_detail": page_data.get("rooms_detail", []),
    }

    return details


def _get_listing_photos(page_data):
    """Build listing photos list."""
    photos = []
    for i, url in enumerate(page_data.get("photo_urls", [])):
        photos.append({
            "url": url,
            "caption": f"listing-photo-{i+1}",
        })
    return photos


# ── Browser Fetching ────────────────────────────────────────────────────────

def _fetch_page_interactive(url):
    """Open a visible browser for Zillow. User solves any CAPTCHA, then we grab the page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n  Playwright is required for Zillow support.")
        print("  Install with: pip install playwright && python3 -m playwright install chromium")
        import subprocess
        print("  Attempting auto-install...")
        subprocess.run(["pip", "install", "playwright"], capture_output=True)
        subprocess.run(["python3", "-m", "playwright", "install", "chromium"], capture_output=True)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ValueError(
                "Playwright is required for Zillow support.\n"
                "Install: pip install playwright && python3 -m playwright install chromium"
            )

    print("  Opening browser to load Zillow listing...")
    print("  If a verification/CAPTCHA appears, please solve it in the browser window.")
    print("  The page will be captured automatically once loaded.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )

        # Mask automation signals
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Poll until the page has the data we need or timeout
            max_wait = 120  # 2 minutes for user to solve CAPTCHA
            poll_interval = 3  # check every 3 seconds
            elapsed = 0

            html = None
            while elapsed < max_wait:
                page.wait_for_timeout(poll_interval * 1000)
                elapsed += poll_interval

                content = page.content()

                # Check if we got past bot protection AND the full page rendered
                # Zillow escapes quotes in embedded JSON, so check both formats
                norm = content.replace('\\"', '"')
                # Wait for resoFacts (detailed property data) OR vrModelGuid (3D tour)
                has_facts = "resoFacts" in norm or "flooring" in norm or "heating" in norm
                has_basic = "streetAddress" in norm or 'zillow_fb:beds' in content
                if has_facts or (has_basic and elapsed >= 12):
                    print("  Page loaded successfully!")
                    # Click all "Show more" buttons to reveal full Facts & features
                    _click_show_more(page)
                    html = page.content()
                    break

                if elapsed % 15 == 0 and elapsed > 0:
                    print(f"  Waiting for page to load... ({elapsed}s)")

            if not html:
                # One final check — grab whatever we have
                html = page.content()
                norm = html.replace('\\"', '"')
                if "streetAddress" not in norm and "zillow_fb:beds" not in html and "zpid" not in norm:
                    raise ValueError(
                        "Timed out waiting for Zillow page to load.\n"
                        "Make sure you solve any CAPTCHA that appears in the browser."
                    )

        except Exception as e:
            if "Timeout" not in str(e):
                raise
            html = page.content()
        finally:
            browser.close()

    if not html:
        raise ValueError("Failed to fetch Zillow listing page.")

    return html


def _click_show_more(page):
    """Click all 'Show more' buttons on the Zillow listing to expand Facts & features."""
    try:
        # Scroll to Facts & features section first
        facts_heading = page.locator("text=Facts & features").first
        if facts_heading.is_visible(timeout=3000):
            facts_heading.scroll_into_view_if_needed()
            page.wait_for_timeout(500)

        # Click all "Show more" buttons
        show_more_buttons = page.locator("button:has-text('Show more'), a:has-text('Show more')")
        count = show_more_buttons.count()
        for i in range(count):
            try:
                btn = show_more_buttons.nth(i)
                if btn.is_visible(timeout=1000):
                    btn.scroll_into_view_if_needed()
                    btn.click(timeout=3000)
                    page.wait_for_timeout(500)
            except Exception:
                pass

        # Wait for content to render
        page.wait_for_timeout(1000)
    except Exception:
        pass  # Non-critical — we still have the basic data
