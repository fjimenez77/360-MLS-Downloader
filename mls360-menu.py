#!/usr/bin/env python3
"""
360 MLS Tour Downloader — Interactive Menu
=================================================
Menu-driven interface for analyzing and downloading MLS virtual tours.

Usage:
    python mls360-menu.py                  # Launch interactive menu
    python mls360-menu.py <url>            # Pre-load a tour URL and launch menu
"""

import json
import os
import sys
import time
from pathlib import Path

# Import the core downloader module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from mls360_downloader_core import (
        load_tour,
        download_tour,
        download_file,
        sanitize_filename,
        make_session,
        get_image_url,
        get_preview_url,
        __version__,
    )
    from mls360_viewer import scan_download_folders, build_viewer_html
except ImportError:
    print("Error: Cannot find mls360_downloader_core.py")
    print("Make sure it's in the same directory as this script.")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    sys.exit(1)


# ── Colors ──────────────────────────────────────────────────────────────────

class C:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


def clr(text, color):
    return f"{color}{text}{C.END}"


# ── Display Helpers ─────────────────────────────────────────────────────────

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def banner():
    print(clr(r"""
  ____  _      _        _____  __    ___
 |  _ \(_) ___| |__    |___ / / /_  / _ \
 | |_) | |/ __| '_ \     |_ \| '_ \| | | |
 |  _ <| | (__| | | |   ___) | (_) | |_| |
 |_| \_\_|\___|_| |_|  |____/ \___/ \___/

    """, C.CYAN))
    print(clr("  MLS Tour Downloader", C.BOLD))
    print(clr("  ─────────────────────────────────────────", C.DIM))
    print()


def print_divider():
    print(clr("  ─────────────────────────────────────────", C.DIM))


def prompt(msg, default=None):
    if default:
        suffix = clr(f" [{default}]", C.DIM)
    else:
        suffix = ""
    val = input(f"  {clr('>', C.GREEN)} {msg}{suffix}: ").strip()
    return val if val else default


def menu_choice(options, title=None):
    if title:
        print(f"\n  {clr(title, C.BOLD)}")
        print_divider()
    for key, label in options:
        print(f"    {clr(key, C.CYAN)}) {label}")
    print()
    return input(f"  {clr('>', C.GREEN)} Choose: ").strip().lower()


# ── Session State ───────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.session = make_session()
        self.tour = None
        self.raw_data = None
        self.provider = None
        self.output_dir = None

    def reset_tour(self):
        self.tour = None
        self.raw_data = None
        self.provider = None
        self.output_dir = None


# ── Core Actions ────────────────────────────────────────────────────────────

def action_set_url(state):
    """Prompt for tour URL and analyze it."""
    print()
    url = prompt("Enter tour URL (Zillow or Ricoh360)")
    if not url:
        print(clr("  No URL entered.", C.YELLOW))
        return

    state.reset_tour()

    try:
        tour, raw_data, provider = load_tour(url, state.session)
        state.tour = tour
        state.raw_data = raw_data
        state.provider = provider
    except ValueError as e:
        print(clr(f"\n  {e}", C.RED))
        return
    except Exception as e:
        print(clr(f"\n  Failed to fetch tour: {e}", C.RED))
        return

    dir_name = sanitize_filename(state.tour['name']) or state.tour['id'][:12]
    downloads = os.path.join(Path.home(), "Downloads")
    state.output_dir = os.path.join(downloads, f"mls360-{dir_name}")

    print()
    print(clr("  Tour loaded successfully!", C.GREEN))
    _print_tour_summary(state.tour)


def _print_tour_summary(tour):
    """Print a compact tour summary."""
    print()
    print_divider()
    print(f"  {clr('Tour:', C.BOLD)}          {tour['name']}")
    print(f"  {clr('Address:', C.BOLD)}       {tour['address']}")
    print(f"  {clr('Provider:', C.BOLD)}      {tour.get('provider', 'unknown')}")
    if tour.get('photographer'):
        print(f"  {clr('Photographer:', C.BOLD)}  {tour['photographer']}")
    print(f"  {clr('Rooms:', C.BOLD)}         {len(tour['rooms'])}")
    enhanced = sum(1 for r in tour['rooms'] if r.get('enhanced'))
    if enhanced:
        print(f"  {clr('Enhanced:', C.BOLD)}      {enhanced}/{len(tour['rooms'])}")
    if tour.get('walkthrough_enabled'):
        print(f"  {clr('Walkthrough:', C.BOLD)}   Yes")
    if tour.get('brand_logo') and tour['brand_logo'].get('url'):
        print(f"  {clr('Brand URL:', C.BOLD)}     {tour['brand_logo']['url']}")
    if tour.get('listing_photos'):
        print(f"  {clr('Photos:', C.BOLD)}        {len(tour['listing_photos'])} listing photos")
    if tour.get('listing_details'):
        details = tour['listing_details']
        if details.get('price') and details['price'] != 'N/A':
            print(f"  {clr('Price:', C.BOLD)}         {details['price']}")
        if details.get('bedrooms') and details['bedrooms'] != 'N/A':
            beds = details['bedrooms']
            baths = details.get('bathrooms', '?')
            sqft = details.get('sqft', '?')
            print(f"  {clr('Size:', C.BOLD)}          {beds} bed / {baths} bath / {sqft}")
    print_divider()


def action_view_rooms(state):
    """Display all rooms with details."""
    if not state.tour:
        print(clr("\n  No tour loaded. Set a URL first.", C.YELLOW))
        return

    print(f"\n  {clr('All Rooms', C.BOLD)} — {state.tour['name']}")
    print_divider()
    print(f"  {'#':>3}  {'Room':<20} {'Status':<12} {'Original':>10} {'Enhanced':>10}")
    print(f"  {'─'*3}  {'─'*20} {'─'*12} {'─'*10} {'─'*10}")

    for room in state.tour['rooms']:
        idx = room['index']
        name = room['name'][:20]
        status = room['enhancement_status']
        has_orig = clr("Yes", C.GREEN) if room['original'] else clr("No", C.RED)
        has_enh = clr("Yes", C.GREEN) if room['enhanced'] else clr("─", C.DIM)

        status_clr = C.GREEN if status == "COMPLETED" else C.YELLOW
        print(f"  {idx:>3}  {name:<20} {clr(status, status_clr):<23} {has_orig:>21} {has_enh:>21}")

    print_divider()
    print(f"  Total: {len(state.tour['rooms'])} rooms")
    enhanced = sum(1 for r in state.tour['rooms'] if r['enhanced'])
    print(f"  Enhanced: {enhanced} | Original only: {len(state.tour['rooms']) - enhanced}")


def action_download_menu(state):
    """Show download options."""
    if not state.tour:
        print(clr("\n  No tour loaded. Set a URL first.", C.YELLOW))
        return

    enhanced_count = sum(1 for r in state.tour['rooms'] if r['enhanced'])
    total = len(state.tour['rooms'])

    choice = menu_choice([
        ("1", f"Download ALL images ({total} original + {enhanced_count} enhanced)"),
        ("2", f"Download ALL images + JSON metadata ({total} original + {enhanced_count} enhanced + JSON)"),
        ("3", f"Download enhanced only ({enhanced_count} rooms)"),
        ("4", f"Download originals only ({total} rooms)"),
        ("5", "Download specific rooms (pick which ones)"),
        ("6", "Download metadata JSON only (no images)"),
        ("b", "Back to main menu"),
    ], title="Download Options")

    if choice == 'b':
        return

    # Set output dir
    print()
    custom_dir = prompt("Output directory", state.output_dir)
    state.output_dir = custom_dir

    if choice == '1':
        _run_download(state, enhanced_only=False, originals_only=False)
    elif choice == '2':
        _save_json_only(state)
        _run_download(state, enhanced_only=False, originals_only=False)
    elif choice == '3':
        _run_download(state, enhanced_only=True, originals_only=False)
    elif choice == '4':
        _run_download(state, enhanced_only=False, originals_only=True)
    elif choice == '5':
        action_download_selective(state)
    elif choice == '6':
        _save_json_only(state)


def action_download_selective(state):
    """Let user pick specific rooms to download."""
    print(f"\n  {clr('Select Rooms to Download', C.BOLD)}")
    print_divider()

    for room in state.tour['rooms']:
        enh = clr(" [E]", C.GREEN) if room['enhanced'] else ""
        idx = room['index']
        rname = room['name']
        print(f"    {idx:>2}) {rname}{enh}")

    print()
    print(f"  Enter room numbers separated by commas (e.g. 1,3,5,10)")
    print(f"  Or a range (e.g. 1-5) or 'all'")
    selection = prompt("Rooms")

    if not selection:
        return

    # Parse selection
    selected_indices = set()
    if selection.lower() == 'all':
        selected_indices = {r['index'] for r in state.tour['rooms']}
    else:
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    selected_indices.update(range(int(start), int(end) + 1))
                except ValueError:
                    print(clr(f"  Invalid range: {part}", C.RED))
                    return
            else:
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    print(clr(f"  Invalid number: {part}", C.RED))
                    return

    # Filter rooms
    selected_rooms = [r for r in state.tour['rooms'] if r['index'] in selected_indices]
    if not selected_rooms:
        print(clr("  No valid rooms selected.", C.YELLOW))
        return

    print(f"\n  Downloading {len(selected_rooms)} rooms...")

    output = Path(state.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    session = state.session
    rooms_dir = output / "rooms"

    for room in selected_rooms:
        idx = room['index']
        name = sanitize_filename(room['name'])
        room_dir = rooms_dir / f"{idx:02d}-{name}"
        room_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  [{idx}/{len(state.tour['rooms'])}] {room['name']}")

        if room.get('original'):
            url = get_image_url(room['original'])
            if url:
                download_file(session, url, room_dir / "original.jpg")
            preview = get_preview_url(room)
            if preview:
                download_file(session, preview, room_dir / "preview.jpg")

        if room.get('enhanced'):
            url = get_image_url(room['enhanced'])
            if url:
                download_file(session, url, room_dir / "enhanced.jpg")

    print(clr(f"\n  Done! Saved to: {output.resolve()}", C.GREEN))


def _run_download(state, enhanced_only=False, originals_only=False):
    """Execute the full download."""
    print(f"\n  Starting download...")
    print_divider()
    download_tour(
        state.tour,
        state.output_dir,
        session=state.session,
        enhanced_only=enhanced_only,
        originals_only=originals_only,
    )
    print(clr(f"\n  Download complete!", C.GREEN))


def _save_json_only(state):
    """Save just the metadata JSON."""
    output = Path(state.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with open(output / "tour-data.json", 'w') as f:
        json.dump(state.tour, f, indent=2)

    with open(output / "tour-raw.json", 'w') as f:
        json.dump(state.raw_data, f, indent=2)

    print(clr(f"\n  Saved JSON to: {output.resolve()}", C.GREEN))
    print(f"    tour-data.json   — parsed tour structure")
    print(f"    tour-raw.json    — raw API response")


def action_view_urls(state):
    """Show direct S3 URLs for all images."""
    if not state.tour:
        print(clr("\n  No tour loaded. Set a URL first.", C.YELLOW))
        return

    print(f"\n  {clr('Direct Image URLs', C.BOLD)} — {state.tour['name']}")
    print_divider()

    for room in state.tour['rooms']:
        idx = room['index']
        rname = room['name']
        print(f"\n  {clr(f'{idx:02d}. {rname}', C.BOLD)}")
        if room['original']:
            print(f"    Original:  {get_image_url(room['original'])}")
        if room['enhanced']:
            print(f"    Enhanced:  {get_image_url(room['enhanced'])}")

    if state.tour.get('brand_logo') and state.tour['brand_logo'].get('s3'):
        print(f"\n  {clr('Brand Logo', C.BOLD)}")
        print(f"    {get_image_url(state.tour['brand_logo'].get('s3') or state.tour['brand_logo'])}")

    print()
    save = prompt("Save URLs to file? (y/n)", "n")
    if save.lower() == 'y':
        output = Path(state.output_dir or '.')
        output.mkdir(parents=True, exist_ok=True)
        url_file = output / "image-urls.txt"
        with open(url_file, 'w') as f:
            f.write(f"# {state.tour['name']} — {state.tour['address']}\n")
            f.write(f"# Photographer: {state.tour['photographer']}\n\n")
            for room in state.tour['rooms']:
                f.write(f"# {room['index']:02d}. {room['name']}\n")
                if room['original']:
                    f.write(f"{get_image_url(room['original'])}\n")
                if room['enhanced']:
                    f.write(f"{get_image_url(room['enhanced'])}\n")
                f.write("\n")
        print(clr(f"  Saved to: {url_file}", C.GREEN))


def action_estimate_size(state):
    """Check file sizes without downloading."""
    if not state.tour:
        print(clr("\n  No tour loaded. Set a URL first.", C.YELLOW))
        return

    print(f"\n  {clr('Checking file sizes...', C.BOLD)}")
    print_divider()

    total_size = 0
    for room in state.tour['rooms']:
        sizes = []
        label = f"  {room['index']:>2}. {room['name']:<20}"

        if room['original']:
            url = get_image_url(room['original'])
            try:
                resp = state.session.head(url, timeout=10)
                size = int(resp.headers.get('Content-Length', 0))
                sizes.append(size)
                total_size += size
            except:
                sizes.append(0)

        if room['enhanced']:
            url = get_image_url(room['enhanced'])
            try:
                resp = state.session.head(url, timeout=10)
                size = int(resp.headers.get('Content-Length', 0))
                sizes.append(size)
                total_size += size
            except:
                sizes.append(0)

        size_str = " + ".join(f"{s/1024/1024:.1f}MB" for s in sizes)
        print(f"{label} {size_str}")

    print_divider()
    print(f"  {clr('Total estimated download:', C.BOLD)} {total_size/1024/1024:.1f} MB")


# ── Viewer Generator ────────────────────────────────────────────────────────

def action_generate_viewer(state):
    """Scan for downloaded tours and generate an HTML 360° viewer."""
    import webbrowser

    print(f"\n  {clr('Build 360° HTML Viewer', C.BOLD)}")
    print_divider()
    print("  Scanning for downloaded tours...")

    folders = scan_download_folders()

    if not folders:
        print(clr("\n  No downloaded tours found in ~/Downloads.", C.YELLOW))
        print(clr("  Download a tour first (option 4), then come back here.", C.DIM))
        return

    # Present folder choices
    options = []
    for i, folder in enumerate(folders):
        label = f"{folder['name']} ({folder['room_count']} rooms)"
        options.append((str(i + 1), label))
    options.append(("b", "Back to main menu"))

    choice = menu_choice(options, title="Select a Tour")

    if choice == 'b':
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(folders):
            print(clr(f"\n  Invalid choice: {choice}", C.RED))
            return
    except ValueError:
        print(clr(f"\n  Invalid choice: {choice}", C.RED))
        return

    selected = folders[idx]
    print(f"\n  Generating viewer for: {clr(selected['name'], C.CYAN)}")
    print(f"  Source: {selected['path']}")

    try:
        output_path = build_viewer_html(selected['path'])
        print(clr(f"\n  Viewer created!", C.GREEN))
        print(f"  File: {output_path}")
        print()

        open_it = prompt("Open in browser? (y/n)", "y")
        if open_it.lower() == 'y':
            webbrowser.open(f"file://{output_path}")
            print(clr("  Opened in browser!", C.GREEN))
        else:
            _print_viewer_instructions(selected['path'])

    except Exception as e:
        print(clr(f"\n  Error generating viewer: {e}", C.RED))


def _print_viewer_instructions(tour_path):
    """Print instructions for launching the viewer manually."""
    mac_cmd = 'cd "' + tour_path + '" && python3 -m http.server 8360'
    win_path = tour_path.replace('/', '\\')
    win_cmd = 'cd /d "' + win_path + '" && python -m http.server 8360'

    print()
    print_divider()
    print(f"  {clr('How to View the 360° Tour', C.BOLD)}")
    print_divider()
    print()
    print(f"  {clr('Mac:', C.CYAN)}")
    print(f"    Option 1: Double-click {clr('Open Tour Viewer.command', C.GREEN)} in the folder")
    print(f"    Option 2: Run in Terminal:")
    print(f"      {clr(mac_cmd, C.DIM)}")
    print()
    print(f"  {clr('Windows:', C.CYAN)}")
    print(f"    Option 1: Double-click {clr('Open Tour Viewer.bat', C.GREEN)} in the folder")
    print(f"    Option 2: Run in CMD or PowerShell:")
    print(f"      {clr(win_cmd, C.DIM)}")
    print()
    print(f"  Then open: {clr('http://localhost:8360/tour-viewer.html', C.BOLD)}")
    print_divider()


# ── Main Menu ───────────────────────────────────────────────────────────────

def main_menu(state):
    """Main interactive menu loop."""
    while True:
        clear_screen()
        banner()

        if state.tour:
            print(f"  {clr('Loaded:', C.GREEN)} {state.tour['name']} — {state.tour['address']}")
            print(f"  {clr('Rooms:', C.DIM)}  {len(state.tour['rooms'])} | "
                  f"Enhanced: {sum(1 for r in state.tour['rooms'] if r['enhanced'])}")
            print()

        options = [
            ("1", "Set target URL (analyze a tour)"),
            ("2", "View tour info"),
            ("3", "View all rooms"),
            ("4", "Download images"),
            ("5", "View direct image URLs"),
            ("6", "Estimate download size"),
            ("7", "Build 360° HTML viewer"),
            ("q", "Quit"),
        ]

        choice = menu_choice(options, title="Main Menu")

        if choice == '1':
            action_set_url(state)
        elif choice == '2':
            if state.tour:
                _print_tour_summary(state.tour)
            else:
                print(clr("\n  No tour loaded. Set a URL first.", C.YELLOW))
        elif choice == '3':
            action_view_rooms(state)
        elif choice == '4':
            action_download_menu(state)
        elif choice == '5':
            action_view_urls(state)
        elif choice == '6':
            action_estimate_size(state)
        elif choice == '7':
            action_generate_viewer(state)
        elif choice == 'q':
            print(clr("\n  Bye!", C.CYAN))
            sys.exit(0)
        else:
            print(clr(f"\n  Invalid choice: {choice}", C.RED))

        print()
        input(clr("  Press Enter to continue...", C.DIM))


def main():
    state = AppState()

    # If URL passed as argument, pre-load it
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        url = sys.argv[1]
        clear_screen()
        banner()
        print(f"  Pre-loading tour: {url}")
        try:
            tour, raw_data, provider = load_tour(url, state.session)
            state.tour = tour
            state.raw_data = raw_data
            state.provider = provider
            dir_name = sanitize_filename(state.tour['name']) or state.tour['id'][:12]
            downloads = os.path.join(Path.home(), "Downloads")
            state.output_dir = os.path.join(downloads, f"mls360-{dir_name}")
            print(clr("  Tour loaded!", C.GREEN))
        except Exception as e:
            print(clr(f"  Failed to load: {e}", C.RED))

    main_menu(state)


if __name__ == "__main__":
    main()
