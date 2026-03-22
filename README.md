<p align="center">
  <img src="logo.svg" alt="360 MLS Downloader" width="200">
</p>

<h1 align="center">360 MLS Downloader</h1>

<p align="center">Download 360-degree panoramic images from Ricoh360 MLS virtual home tours.<br>Supports both an interactive menu-driven interface and a scriptable CLI for automation.</p>

Built by **PRHack | CyberSpartan77** ([@fjimenez77](https://github.com/fjimenez77))

---

## Features

- Download all 360 equirectangular panoramas from any Ricoh360 MLS tour
- Interactive menu mode with tour analysis, room selection, and size estimation
- CLI mode with flags for scripting and automation
- Downloads both original and AI-enhanced versions
- Selective room downloads (pick specific rooms or ranges)
- Exports direct S3 image URLs for use in other tools
- Resume support — skips already-downloaded files
- Saves full tour metadata as JSON

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
ricoh360-Tour-Name/
  tour-data.json              # Full tour metadata
  brand-logo.jpg              # Photographer's brand logo
  tripod-cover.jpg            # Tripod cover overlay
  rooms/
    01-Foyer/
      original.jpg            # Original 360 panorama
      preview.jpg             # Smaller preview version
      enhanced.jpg            # AI-enhanced version
      enhanced-preview.jpg    # Enhanced preview
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

---

## Interactive Menu Options

| Option | Description |
|--------|-------------|
| **1. Set target URL** | Enter a Ricoh360 tour URL to analyze |
| **2. View tour info** | Show address, photographer, room count, features |
| **3. View all rooms** | Table of all rooms with original/enhanced status |
| **4. Download images** | Submenu: all, enhanced-only, originals-only, selective, or JSON-only |
| **5. View direct URLs** | Show/save all direct S3 image URLs |
| **6. Estimate size** | Check total download size before downloading |
| **q. Quit** | Exit the application |

### Selective Downloads

In the download menu, option `4` lets you pick specific rooms:

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
| `--output`, `-o` | Set custom output directory |
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

No authentication required — MLS tour data and images are publicly accessible by design (they're meant to be shared with home buyers).

---

## Credits

**Author:** PRHack | CyberSpartan77 ([@fjimenez77](https://github.com/fjimenez77))

API reverse-engineering powered by [AuthScope](https://github.com/fjimenez77/AuthScope) Chrome Extension and manual network analysis.

---

## Disclaimer

This tool is intended for downloading your own property tour images or tours you have permission to use. Respect photographers' copyright and licensing agreements. The images may be owned by the photographer or real estate agency — verify your usage rights before republishing.

---

## License

MIT License — see [LICENSE](LICENSE) file.
