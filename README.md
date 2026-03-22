<p align="center">
  <img src="logo.svg" alt="360 MLS Downloader" width="200">
</p>

<h1 align="center">360 MLS Downloader</h1>

<p align="center">Download 360-degree panoramic images from Ricoh360 MLS virtual home tours.<br>Supports both an interactive menu-driven interface and a scriptable CLI for automation.</p>

<p align="center"><strong>v1.0.0</strong></p>

Built by **PRHack | CyberSpartan77** ([@fjimenez77](https://github.com/fjimenez77))

---

## Features

- Download all 360 equirectangular panoramas from any Ricoh360 MLS tour
- Interactive menu mode with tour analysis, room selection, and size estimation
- CLI mode with flags for scripting and automation
- Downloads both original and AI-enhanced versions
- Selective room downloads (pick specific rooms or ranges)
- Generate a self-contained 360° HTML tour viewer for offline use
- Exports direct S3 image URLs for use in other tools
- Resume support — skips already-downloaded files
- Saves full tour metadata as JSON
- Includes usage instructions for uploading to Zillow, Realtor.com, and other platforms

## Requirements

- Python 3.8+
- `requests` library

## Installation

```bash
git clone https://github.com/fjimenez77/360-MLS-Downloader.git
cd 360-MLS-Downloader
pip install requests
```

---

## Quick Start

### Interactive Menu

```bash
python3 ricoh360-menu.py
```

This launches a full interactive menu where you can:

1. Paste any Ricoh360 tour URL
2. View tour details (address, photographer, room count)
3. Browse all rooms with enhancement status
4. Choose what to download
5. View direct image URLs
6. Estimate total download size before committing
7. Build a 360° HTML viewer for offline use

You can also pre-load a tour URL:

```bash
python3 ricoh360-menu.py "https://mls.ricoh360.com/YOUR-TOUR-ID/ROOM-ID"
```

### CLI Mode (Advanced)

```bash
# Download everything from a tour
python3 ricoh360-downloader.py "https://mls.ricoh360.com/TOUR-ID/ROOM-ID"

# Just the tour UUID works too
python3 ricoh360-downloader.py f948586f-1c5c-48dc-81fd-6ef9a09a12c0

# Custom output directory
python3 ricoh360-downloader.py TOUR-URL --output ~/Desktop/my-listing

# Only AI-enhanced images
python3 ricoh360-downloader.py TOUR-URL --enhanced-only

# Only originals (skip enhanced)
python3 ricoh360-downloader.py TOUR-URL --originals-only

# Just grab metadata JSON, no images
python3 ricoh360-downloader.py TOUR-URL --json-only
```

---

## Usage Guide

### Step 1: Get the Tour URL

Open any Ricoh360 MLS virtual tour in your browser. The URL looks like:

```
https://mls.ricoh360.com/f948586f-1c5c-48dc-81fd-6ef9a09a12c0/c84e8d06-2b82-46a0-991a-8814573e048b
```

The first UUID is the **tour ID**, the second is the current **room ID**. You only need the tour ID — the tool extracts it automatically from any Ricoh360 URL.

### Step 2: Run the Downloader

**Option A — Interactive Menu:**

```bash
python3 ricoh360-menu.py
```

Then select option `1` and paste the URL. The tool will:
- Fetch the tour data from Ricoh360's API
- Show you tour details, room list, and enhancement status
- Let you choose what to download

**Option B — CLI:**

```bash
python3 ricoh360-downloader.py "https://mls.ricoh360.com/TOUR-ID"
```

### Step 3: Use Your Images

Downloaded files are organized like this:

```
~/Downloads/ricoh360-Tour-Name/
  HOW TO USE THESE IMAGES.txt   # Usage instructions for online platforms
  tour-data.json                # Full tour metadata
  tour-raw.json                 # Raw API response
  brand-logo.jpg                # Photographer's brand logo
  tripod-cover.jpg              # Tripod cover overlay
  tour-viewer.html              # 360° viewer (generated via option 7)
  Open Tour Viewer.command      # Mac launcher (generated via option 7)
  Open Tour Viewer.bat          # Windows launcher (generated via option 7)
  rooms/
    01-Foyer/
      original.jpg              # Original 360 panorama
      preview.jpg               # Smaller preview version
      enhanced.jpg              # AI-enhanced version (if available)
      enhanced-preview.jpg      # Enhanced preview (if available)
    02-Kitchen/
      original.jpg
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
- Use `enhanced.jpg` versions when available (better lighting and color)
- Upload rooms in order (01, 02, 03...) to keep the tour flow logical
- Each image is 3-4 MB, within most platform upload limits

A detailed instructions file (`HOW TO USE THESE IMAGES.txt`) is included in every download.

---

## Interactive Menu Options

| Option | Description |
|--------|-------------|
| **1. Set target URL** | Enter a Ricoh360 tour URL to analyze |
| **2. View tour info** | Show address, photographer, room count, features |
| **3. View all rooms** | Table of all rooms with original/enhanced status |
| **4. Download images** | Submenu: all, all + JSON metadata, enhanced-only, originals-only, selective, or JSON-only |
| **5. View direct URLs** | Show/save all direct S3 image URLs |
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
| `--output`, `-o` | Set custom output directory (default: `~/Downloads/ricoh360-<tour-name>`) |
| `--enhanced-only` | Only download AI-enhanced images |
| `--originals-only` | Only download original images |
| `--json-only` | Save tour metadata JSON without downloading images |

---

## File Structure

```
360-MLS-Downloader/
  ricoh360-menu.py              # Interactive menu interface
  ricoh360-downloader.py        # CLI interface
  ricoh360_downloader_core.py   # Shared core engine (all logic)
  ricoh360_viewer.py            # 360° HTML viewer generator
  vendor/
    pannellum.min.js            # Pannellum 2.5.6 (MIT) — 360° viewer
    pannellum.min.css
  logo.svg
  README.md
  LICENSE
```

---

## How It Works

Ricoh360 MLS tours are built with Next.js and store 360 panoramic images in AWS S3. The tool:

1. Extracts the tour UUID from the URL
2. Fetches the Next.js build ID from the main page
3. Calls the Next.js data endpoint to get full tour metadata (rooms, image keys, S3 bucket info)
4. Constructs direct S3 URLs for each panoramic image
5. Downloads images with retry logic and resume support
6. Optionally generates a self-contained HTML 360° viewer using Pannellum

No authentication required — MLS tour data and images are publicly accessible by design (they're meant to be shared with home buyers).

---

## Credits

**Author:** PRHack | CyberSpartan77 ([@fjimenez77](https://github.com/fjimenez77))

API reverse-engineering powered by [AuthScope](https://github.com/fjimenez77/AuthScope) Chrome Extension and manual network analysis.

360° viewer powered by [Pannellum](https://pannellum.org/) (MIT License).

---

## Contributing

Want to help improve this tool? Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to fork, branch, and submit a pull request.

---

## Disclaimer

This tool is intended for downloading your own property tour images or tours you have permission to use. Respect photographers' copyright and licensing agreements. The images may be owned by the photographer or real estate agency — verify your usage rights before republishing.

---

## License

MIT License — see [LICENSE](LICENSE) file.
