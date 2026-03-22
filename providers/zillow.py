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

    # Description
    desc_match = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', h)
    if desc_match:
        try:
            data["description"] = desc_match.group(1).encode().decode('unicode_escape')
        except Exception:
            data["description"] = desc_match.group(1)

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
                if val and val != ["None"]:
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
        "propertySubType": ("property_subtype", str),
        "garageSpaces": ("garage_spaces", int),
        "totalParkingSpaces": ("total_parking", int),
        "lotSizeDimensions": ("lot_dimensions", str),
    }
    for json_key, (data_key, conv) in scalar_facts.items():
        m = re.search(rf'"{json_key}"\s*:\s*"?([^,"\]]+)"?', h)
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

    return data


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
        "fencing": fmt_list(page_data.get("fencing")),
        # Construction
        "builder": page_data.get("builder_name", ""),
        # Utilities
        "electric": fmt_list(page_data.get("electric")),
        "water": fmt_list(page_data.get("water_source")),
        "sewer": fmt_list(page_data.get("sewer")),
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

                # Check if we got past bot protection
                # Zillow escapes quotes in embedded JSON, so check both formats
                norm = content.replace('\\"', '"')
                if "vrModelGuid" in norm or "streetAddress" in norm or 'zillow_fb:beds' in content:
                    print("  Page loaded successfully!")
                    html = content
                    break

                if elapsed % 15 == 0 and elapsed > 0:
                    print(f"  Waiting for page to load... ({elapsed}s)")

            if not html:
                # One final check
                html = page.content()
                norm = html.replace('\\"', '"')
                if "vrModelGuid" not in norm and "streetAddress" not in norm and "zillow_fb:beds" not in html:
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
