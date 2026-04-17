<p align="center">
  <img src="Logo/logo.svg" alt="360 MLS Downloader" width="200">
</p>

<h1 align="center">360 MLS Downloader</h1>

<p align="center">Download 360° panoramic images and listing photos from MLS virtual home tours.<br>Built by a homeowner who wanted to archive the listing of the house he bought before it rotated off the listing site.</p>

<p align="center"><strong>v2.0.0</strong></p>

Built by **PRHack | CyberSpartan77** ([@fjimenez77](https://github.com/fjimenez77))

---

## Purpose and intended use

I built this tool for myself. I bought a house, and the listing had a beautiful 360° virtual tour and dozens of professional photos of what is now my home. Listings rotate off the listing site within weeks of closing, so I wanted to archive those images before they disappeared — every one of them is visible on the public listing page and can be saved manually by any visitor with some patience. This tool just automates the click-save-rename-organize loop so I didn't have to do it ninety times by hand.

**That's the use case this tool exists for:**

- Homeowners archiving the listing media of a home they've purchased, before it rotates off the platform
- Sellers preserving the listing media of their own property
- Anyone with explicit permission from the photographer or rightsholder to download the images

**That's not the use case this tool exists for:**

- Bulk-scraping listings you have no personal connection to
- Building a competing listings database, a price-tracking service, or any commercial data product
- Republishing another photographer's or agency's work commercially
- Any use that violates a platform's Terms of Service or infringes a photographer's copyright

Nothing this tool does is something you couldn't do by opening the listing in your browser and saving the images by hand. It just does it faster for the person it was built for.

---

## Supported Platforms

| Platform | What You Get |
|----------|-------------|
| **Zillow 3D Home** | 360° panoramas (4K JPEG + 8K AVIF), all listing photos, property details (price, beds, baths, sqft, lot, year built), full description |
| **Zillow (no 3D)** | All listing photos, property details, description — works on any Zillow listing |
| **Ricoh360 MLS** | 360° panoramas (original + AI-enhanced), tour metadata, photographer info |

## Features

- Auto-detects platform from URL — just paste and go
- Download all 360° equirectangular panoramas from MLS virtual tours
- **Zillow:** Downloads listing photos, property description, price, beds/baths/sqft, year built, lot size, MLS #
- **Zillow:** Works with or without a 3D tour — grabs everything available on the listing
- **Zillow:** Opens a browser for CAPTCHA solving if needed (user solves, app continues automatically)
- Interactive menu mode with tour analysis, room selection, and size estimation
- CLI mode with flags for scripting and automation
- Downloads both original and AI-enhanced/8K versions
- Selective room downloads (pick specific rooms or ranges)
- Generate a self-contained 360° HTML tour viewer for offline use
- Resume support — skips already-downloaded files
- Saves full tour metadata as JSON
- Includes usage instructions for uploading to real estate platforms
- Cross-platform: Mac and Windows support

## Requirements

- Python 3.10+ (tested on 3.14)
- `requests` library
- `playwright` (required for Zillow — auto-installs on first use)

## Installation

```bash
git clone https://github.com/fjimenez77/360-MLS-Downloader.git
cd 360-MLS-Downloader
pip install requests
```

For Zillow support, Playwright will auto-install on first use. Or install manually:

```bash
pip install playwright
python3 -m playwright install chromium
```

---

## Quick Start

### Interactive Menu

```bash
python3 mls360-menu.py
```

This launches a full interactive menu where you can:

1. Paste any tour URL (Zillow or Ricoh360 — auto-detected)
2. View tour details (address, photographer, price, room count)
3. Browse all rooms with enhancement status
4. Choose what to download
5. View direct image URLs
6. Estimate total download size before committing
7. Build a 360° HTML viewer for offline use

You can also pre-load a tour URL:

```bash
python3 mls360-menu.py "https://www.zillow.com/homedetails/ADDRESS/ZPID_zpid/"
python3 mls360-menu.py "https://mls.ricoh360.com/TOUR-ID/ROOM-ID"
```

### CLI Mode (Advanced)

```bash
# Download a Zillow listing (3D tour + photos + details)
python3 mls360-downloader.py "https://www.zillow.com/homedetails/ADDRESS/ZPID_zpid/"

# Download a Ricoh360 tour
python3 mls360-downloader.py "https://mls.ricoh360.com/TOUR-ID/ROOM-ID"

# Just the tour UUID works too (Ricoh360)
python3 mls360-downloader.py f948586f-1c5c-48dc-81fd-6ef9a09a12c0

# Custom output directory
python3 mls360-downloader.py TOUR-URL --output ~/Desktop/my-listing

# Only AI-enhanced/8K images
python3 mls360-downloader.py TOUR-URL --enhanced-only

# Only originals/4K (skip enhanced)
python3 mls360-downloader.py TOUR-URL --originals-only

# Just grab metadata JSON, no images
python3 mls360-downloader.py TOUR-URL --json-only
```

---

## Usage Guide

### Step 1: Get the URL

**For Zillow** — copy the listing URL from your browser:
```
https://www.zillow.com/homedetails/9123-Pitcairn-San-Antonio-TX-78254/26433581_zpid/
```

**For Ricoh360** — copy the tour URL:
```
https://mls.ricoh360.com/f948586f-1c5c-48dc-81fd-6ef9a09a12c0/c84e8d06-2b82-46a0-991a-8814573e048b
```

### Step 2: Run the Downloader

```bash
python3 mls360-menu.py
```

Select option `1`, paste the URL. The tool auto-detects the platform and:
- Fetches tour/listing data
- Shows details (address, rooms, price, photos)
- Lets you choose what to download

For Zillow: a browser window opens briefly to load the page. If a CAPTCHA appears, solve it — the app continues automatically once the page loads.

### Step 3: Use Your Images

**Zillow download output:**

```
~/Downloads/mls360-Address/
  HOW TO USE THESE IMAGES.txt   # Usage instructions
  listing-details.txt           # Price, beds, baths, sqft, description
  tour-data.json                # Full tour metadata
  photos/                       # All listing photos
    01-listing-photo-1.jpg
    02-listing-photo-2.webp
    ...
  rooms/                        # 360° panoramas (if 3D tour exists)
    01-Front-yard/
      original.jpg              # 4K panorama (JPEG)
      preview.jpg               # Thumbnail
      enhanced.avif             # 8K panorama (AVIF, when available)
    02-Entrance/
      ...
```

**Ricoh360 download output:**

```
~/Downloads/mls360-Tour-Name/
  HOW TO USE THESE IMAGES.txt   # Usage instructions
  tour-data.json                # Full tour metadata
  brand-logo.jpg                # Photographer's brand logo
  tripod-cover.jpg              # Tripod cover overlay
  rooms/
    01-Foyer/
      original.jpg              # Original 360 panorama
      preview.jpg               # Smaller preview
      enhanced.jpg              # AI-enhanced version (if available)
      enhanced-preview.jpg      # Enhanced preview
    02-Kitchen/
      ...
```

**Image format:** JPEG equirectangular projection — standard 360 format supported by:
- MLS platforms (Zillow, Realtor.com, Redfin)
- 360 tour builders (Kuula, CloudPano, Matterport)
- Social media (Facebook 360 photos, YouTube 360)
- VR headsets
- Any panorama viewer

### Step 4 (Optional): Build a 360° HTML Viewer

Use menu option `7` to generate a self-contained HTML tour viewer from any downloaded tour:

1. Select option `7` from the main menu
2. Pick a downloaded tour folder
3. The tool generates `tour-viewer.html` in that folder
4. Launch it using the included scripts:
   - **Mac:** Double-click `Open Tour Viewer.command`
   - **Windows:** Double-click `Open Tour Viewer.bat`

The viewer includes a sidebar with room thumbnails, previous/next navigation, keyboard controls (arrow keys), and works completely offline.

---

## Uploading to Real Estate Platforms

The downloaded images are standard equirectangular JPEGs — most platforms auto-detect them as 360° photos:

| Platform | How to Upload |
|----------|---------------|
| **Zillow (FSBO)** | Upload room images as regular photos — Zillow auto-detects 360° format |
| **Realtor.com** | Upload through your listing dashboard |
| **Redfin** | Upload through the listing photo manager |
| **MLS** | Upload via your agent or FSBO MLS service |
| **Facebook** | Upload as a "360 Photo" — auto-detected |
| **Kuula / CloudPano** | Upload equirectangular JPEGs to create interactive tours |

**Tips:**
- Use `enhanced` versions when available (better lighting and color)
- Upload rooms in order (01, 02, 03...) to keep the tour flow logical
- Each image is typically under 2 MB, within most platform upload limits

A detailed instructions file (`HOW TO USE THESE IMAGES.txt`) is included in every download.

---

## Interactive Menu Options

| Option | Description |
|--------|-------------|
| **1. Set target URL** | Enter a tour URL (Zillow or Ricoh360 — auto-detected) |
| **2. View tour info** | Show address, photographer, price, room count, listing details |
| **3. View all rooms** | Table of all rooms with original/enhanced status |
| **4. Download images** | Submenu: all, all + JSON, enhanced-only, originals-only, selective, JSON-only |
| **5. View direct URLs** | Show/save all direct image URLs |
| **6. Estimate size** | Check total download size before downloading |
| **7. Build 360° viewer** | Generate an offline HTML tour viewer from a downloaded tour |
| **q. Quit** | Exit the application |

### Selective Downloads

In the download menu, option `5` lets you pick specific rooms:

```
Enter room numbers: 1,3,5,10      # Individual rooms
Enter room numbers: 1-5            # Range
Enter room numbers: 1-5,10,15-20   # Mixed
Enter room numbers: all            # Everything
```

---

## CLI Flags

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Set custom output directory (default: `~/Downloads/mls360-<name>`) |
| `--enhanced-only` | Only download enhanced/8K images |
| `--originals-only` | Only download original/4K images |
| `--json-only` | Save tour metadata JSON without downloading images |
| `--version` | Show version number |

---

## File Structure

```
360-MLS-Downloader/
  mls360-menu.py              # Interactive menu interface
  mls360-downloader.py        # CLI interface
  mls360_downloader_core.py   # Shared core engine (provider-agnostic)
  mls360_viewer.py            # 360° HTML viewer generator
  providers/
    __init__.py               # Provider registry and auto-detection
    zillow.py                 # Zillow 3D Home + listing provider
    ricoh360.py               # Ricoh360 MLS provider
  vendor/
    pannellum.min.js          # Pannellum 2.5.6 (MIT) — 360° viewer
    pannellum.min.css
  logo.svg
  README.md
  LICENSE
  CONTRIBUTING.md
```

---

## How It Works

The tool uses a multi-provider architecture to support different platforms:

**Zillow:**
1. Opens a browser to load the listing page (bypasses bot protection)
2. Extracts property details, photo URLs, and 3D tour IDs from the page
3. Fetches the IMX manifest from Zillow's CDN (public, no auth)
4. Downloads 4K/8K panoramas, listing photos, and saves property details

**Ricoh360:**
1. Extracts the tour UUID from the URL
2. Fetches the Next.js build ID from the main page
3. Calls the Next.js data endpoint for full tour metadata
4. Constructs direct S3 URLs and downloads all images

Both providers output to the same folder structure, and the 360° HTML viewer works with either.

---

## Credits

**Author:** PRHack | CyberSpartan77 ([@fjimenez77](https://github.com/fjimenez77))

API reverse-engineering powered by [AuthScope](https://github.com/fjimenez77/AuthScope) Chrome Extension and manual network analysis.

360° viewer powered by [Pannellum](https://pannellum.org/) (MIT License).

---

## Contributing

Pull requests, bug reports, and feature suggestions are welcome.

**Quick version:**

```bash
# 1. Fork the repo on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/360-MLS-Downloader.git
cd 360-MLS-Downloader

# 3. Create a feature branch
git checkout -b feature/your-idea

# 4. Make changes, test locally
python3 mls360-menu.py
python3 -m py_compile mls360-menu.py

# 5. Commit + push + open a PR
git commit -m "Add: your change"
git push origin feature/your-idea
```

**Before opening a PR:**

- Open an issue first for non-trivial changes
- Keep PRs focused (one logical change per PR)
- Test the affected functionality manually
- No new external dependencies without discussion
- No real credentials, API keys, or PII in commits

**Reporting bugs?** Include your OS, Python version, and reproduction steps.

**Found a security issue?** Don't open a public issue — use [GitHub Security Advisories](https://github.com/fjimenez77/360-MLS-Downloader/security/advisories) instead.

---

## Contributors

- [@fjimenez77](https://github.com/fjimenez77) (Felix J.)
- [@netsecops-76](https://github.com/netsecops-76) (Brian Canaday)
- [@DevForgeAtlas](https://github.com/DevForgeAtlas)

---

## Design Principles

This project is built around one rule: **a human must be the one who satisfies the CAPTCHA when a site presents one.** The Playwright browser window opens visibly on purpose — the user sees the challenge, solves it, and the script resumes. That's not a workaround for a missing feature. It *is* the feature.

Contributions that remove the human from that loop will not be accepted. The following are explicitly out of scope, and PRs implementing them will be closed regardless of code quality:

- Integration with commercial CAPTCHA-solving services (2Captcha, CapSolver, Anti-Captcha, NopeCHA, or equivalents) — whether enabled by default, opt-in, or behind a flag
- Switching the Playwright browser to headless mode on any code path that can encounter a CAPTCHA
- Bundling, recommending, or auto-configuring residential or mobile proxy providers intended to evade bot detection
- Browser fingerprint spoofing, WebDriver-property hiding, stealth plugins, or other anti-detect techniques aimed at making the automation indistinguishable from a human session
- Any mechanism whose purpose is to defeat a site's bot detection rather than satisfy it

**Why the hard line.** Manually solving a CAPTCHA that your own browser shows you is a human completing the challenge the site designed. Programmatically defeating or hiding from bot detection is something else — it materially changes the legal posture of the tool under the CFAA, DMCA §1201, and the Terms of Service of every platform it touches, and it changes the exposure for every contributor whose name is in the git log. Keeping a human in the loop is what makes this a convenience wrapper, not a bypass tool.

Performance work, new providers, bug fixes, better UX around the manual-solve step, clearer errors, and refactors are all welcome. The line is specifically about removing the human, not about improving the tool around them.

---

## What This Tool Does Not Do

These are deliberate design choices, not missing features:

- **No automated CAPTCHA solving.** When a platform shows a CAPTCHA, a visible browser window opens and you solve it yourself. The script waits.
- **No headless browser on the Zillow path.** You see what the tool is doing at every step.
- **No proxy rotation, IP masking, or anti-detect fingerprinting.** The tool identifies itself as what it is — a regular browser session controlled by the person running it.
- **No bulk/batch ingestion of listings you don't specify.** One URL at a time, by hand.
- **No scheduling, cron, or unattended operation.** It runs when you run it.
- **No cloud hosting, no SaaS offering, no hosted version.** Local execution only.
- **No account credentials stored or required.** It doesn't log in as you; it views what any logged-out visitor can view.
- **No redistribution mechanism.** It downloads to your machine. What you do with the files afterward is on you, and your obligations to the copyright holder don't change because a script helped you download.

---

## A Note on Copyright

Buying a house does not automatically transfer copyright in the listing photos to you. Under copyright law in most jurisdictions, the photographer retains ownership of the images unless there's a written agreement saying otherwise — even when those images are of a property you now own. In practice this means:

- **Personal archival use** (keeping the tour images for your own records, showing them to family, remembering what the house looked like when you bought it) is the use case this tool was built around, and it's the use case least likely to concern anyone.
- **Republishing** the images — especially for commercial purposes like listing the home on Airbnb, a short-term rental site, a business website, or in marketing materials — may require the photographer's permission regardless of the fact that you own the house. Check with your agent or the seller whether image rights were included in your purchase; often they aren't, and often nobody thought to ask.

The tool downloads what you could manually save from a public listing page. What you do with the images afterward is governed by copyright law, not by this tool and not by the Apache 2.0 license it's released under.

---

## Your Responsibilities as a User

Running this tool is your decision, and the consequences of running it are yours. Before using it, you should be able to affirm:

1. **You have a legitimate connection to the property** — you bought it, you sold it, you own it, you're the photographer, or you have explicit permission from someone who does.
2. **You understand the photographer likely retains copyright** on the images, and you will not republish them commercially without confirming rights. (See the copyright note above.)
3. **You have read the Terms of Service of the platform you're pointing it at.** Those terms bind you, the user — not this tool, not the author.
4. **You will stop if asked.** If a platform or rightsholder asks you to stop or to remove images, stop and remove them.

If you can't honestly affirm the first two, this tool isn't for you. Open the listing in your browser and decide whether you can save the images by hand; if you can't justify doing it manually, automating it doesn't change the answer.

---

## Not Affiliated

This project is not affiliated with, endorsed by, or sponsored by Zillow Group, Ricoh Company Ltd., Ricoh360, MLS, Pannellum, or any real estate platform, brokerage, or photography service. All trademarks are the property of their respective owners. Mentions of these services in this README describe interoperability only.

---

## Contact

Questions, concerns, or feedback? Reach out via [GitHub Issues](https://github.com/fjimenez77/360-MLS-Downloader/issues) or email the author directly.

---

## Support

This tool is provided as-is with no support obligation. Platforms change their layouts, APIs, and bot-detection systems regularly; when they do, parts of this tool will break, and there is no guarantee of a fix. If something stops working, you are welcome to open an issue — but an unanswered issue is not a bug in your contract with me, because there is no contract. The Apache 2.0 license's warranty disclaimer covers this formally; this paragraph says it in English.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for full text.

Copyright 2026 Felix J. ([@fjimenez77](https://github.com/fjimenez77)) and contributors

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0
