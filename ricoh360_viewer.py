#!/usr/bin/env python3
"""
Ricoh360 360° HTML Viewer Generator
=====================================
Generates a self-contained HTML page for viewing downloaded 360° panoramas
locally in a browser — no internet required.

Uses Pannellum (MIT) for equirectangular panorama rendering.
"""

import json
import os
import re
from pathlib import Path


VENDOR_DIR = Path(__file__).parent / "vendor"


def scan_download_folders(base_dir=None):
    """Scan for ricoh360-* folders in ~/Downloads (or custom base)."""
    if base_dir is None:
        base_dir = Path.home() / "Downloads"
    else:
        base_dir = Path(base_dir)

    if not base_dir.exists():
        return []

    folders = []
    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir() and entry.name.startswith("ricoh360-"):
            rooms_dir = entry / "rooms"
            if rooms_dir.exists() and rooms_dir.is_dir():
                room_count = sum(1 for d in rooms_dir.iterdir() if d.is_dir())
                display_name = entry.name.replace("ricoh360-", "").replace("-", " ")
                folders.append({
                    "path": str(entry),
                    "name": display_name,
                    "folder_name": entry.name,
                    "room_count": room_count,
                })
    return folders


def _pick_image(room_dir, candidates):
    """Pick the first existing image from candidates list."""
    for name in candidates:
        path = room_dir / name
        if path.exists() and path.stat().st_size > 0:
            return name
    return None


def _parse_room_folder(folder_name):
    """Extract index and name from folder like '01-Foyer'."""
    match = re.match(r'^(\d+)-(.+)$', folder_name)
    if match:
        return int(match.group(1)), match.group(2).replace("-", " ")
    return 0, folder_name


def build_viewer_html(tour_folder):
    """Generate tour-viewer.html in the given tour folder."""
    tour_folder = Path(tour_folder)
    rooms_dir = tour_folder / "rooms"

    if not rooms_dir.exists():
        raise FileNotFoundError(f"No rooms/ directory in {tour_folder}")

    # Load tour metadata if available
    tour_name = tour_folder.name.replace("ricoh360-", "").replace("-", " ")
    address = ""
    photographer = ""

    tour_json = tour_folder / "tour-data.json"
    if tour_json.exists():
        with open(tour_json) as f:
            data = json.load(f)
            tour_name = data.get("name", tour_name)
            address = data.get("address", "")
            photographer = data.get("photographer", "")

    # Scan room folders
    rooms = []
    for entry in sorted(rooms_dir.iterdir()):
        if not entry.is_dir():
            continue

        idx, name = _parse_room_folder(entry.name)
        panorama = _pick_image(entry, ["enhanced.jpg", "original.jpg"])
        if not panorama:
            continue

        preview = _pick_image(entry, ["enhanced-preview.jpg", "preview.jpg"])

        rooms.append({
            "index": idx,
            "name": name,
            "folder": entry.name,
            "panorama": f"rooms/{entry.name}/{panorama}",
            "preview": f"rooms/{entry.name}/{preview}" if preview else None,
            "has_enhanced": (panorama == "enhanced.jpg"),
        })

    if not rooms:
        raise ValueError(f"No rooms with images found in {rooms_dir}")

    # Load Pannellum vendor files
    pannellum_js = (VENDOR_DIR / "pannellum.min.js").read_text()
    pannellum_css = (VENDOR_DIR / "pannellum.min.css").read_text()

    # Build scenes JSON for Pannellum
    scenes = {}
    for room in rooms:
        scene_id = f"scene-{room['index']}"
        scenes[scene_id] = {
            "title": room["name"],
            "panorama": room["panorama"],
            "type": "equirectangular",
            "autoLoad": True,
            "hfov": 120,
        }

    scenes_json = json.dumps(scenes, indent=2)
    rooms_json = json.dumps(rooms, indent=2)
    first_scene = f"scene-{rooms[0]['index']}"

    # Build HTML
    html = _build_html(
        tour_name=tour_name,
        address=address,
        photographer=photographer,
        pannellum_css=pannellum_css,
        pannellum_js=pannellum_js,
        scenes_json=scenes_json,
        rooms_json=rooms_json,
        first_scene=first_scene,
        room_count=len(rooms),
    )

    output_path = tour_folder / "tour-viewer.html"
    with open(output_path, "w") as f:
        f.write(html)

    # Generate launcher script for macOS
    launcher_path = tour_folder / "Open Tour Viewer.command"
    launcher_script = f'''#!/bin/bash
# 360° Tour Viewer Launcher
# Starts a local web server and opens the tour in your browser.
# Close this terminal window to stop the server.

cd "$(dirname "$0")"
PORT=8360

# Find an open port if 8360 is taken
while lsof -i :$PORT > /dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo ""
echo "  Starting 360° Tour Viewer..."
echo "  Tour: {tour_name}"
echo "  URL:  http://localhost:$PORT/tour-viewer.html"
echo ""
echo "  Close this window to stop the server."
echo ""

# Open browser after a short delay
(sleep 1 && open "http://localhost:$PORT/tour-viewer.html") &

# Start server
python3 -m http.server $PORT
'''
    with open(launcher_path, "w") as f:
        f.write(launcher_script)
    os.chmod(launcher_path, 0o755)

    # Generate launcher script for Windows
    bat_path = tour_folder / "Open Tour Viewer.bat"
    bat_script = f'''@echo off
title 360 Tour Viewer - {tour_name}
echo.
echo   Starting 360 Tour Viewer...
echo   Tour: {tour_name}
echo.
echo   Close this window to stop the server.
echo.

cd /d "%~dp0"
set PORT=8360

REM Open browser after a short delay
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:%PORT%/tour-viewer.html"

REM Start server
python -m http.server %PORT%
'''
    with open(bat_path, "w") as f:
        f.write(bat_script)

    return str(output_path)


def _build_html(tour_name, address, photographer, pannellum_css, pannellum_js,
                scenes_json, rooms_json, first_scene, room_count):
    """Assemble the full HTML document."""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape_html(tour_name)} — 360° Tour</title>
<style>
{pannellum_css}
</style>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    display: flex;
}}

/* Sidebar */
#sidebar {{
    width: 300px;
    min-width: 300px;
    height: 100vh;
    background: #1e293b;
    display: flex;
    flex-direction: column;
    border-right: 1px solid #334155;
    z-index: 100;
    transition: transform 0.3s ease;
}}

#sidebar.collapsed {{
    transform: translateX(-300px);
    min-width: 0;
    width: 0;
}}

#sidebar-header {{
    padding: 20px;
    border-bottom: 1px solid #334155;
    flex-shrink: 0;
}}

#sidebar-header h1 {{
    font-size: 18px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 6px;
}}

#sidebar-header .address {{
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 4px;
}}

#sidebar-header .photographer {{
    font-size: 12px;
    color: #64748b;
}}

#sidebar-header .room-count {{
    font-size: 12px;
    color: #38bdf8;
    margin-top: 8px;
}}

/* Room list */
#room-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}}

#room-list::-webkit-scrollbar {{
    width: 6px;
}}

#room-list::-webkit-scrollbar-track {{
    background: #1e293b;
}}

#room-list::-webkit-scrollbar-thumb {{
    background: #475569;
    border-radius: 3px;
}}

.room-btn {{
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    margin-bottom: 4px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
    color: #cbd5e1;
    font-size: 14px;
}}

.room-btn:hover {{
    background: #334155;
    border-color: #475569;
}}

.room-btn.active {{
    background: #0f172a;
    border-color: #38bdf8;
    color: #f1f5f9;
}}

.room-btn .room-thumb {{
    width: 56px;
    height: 32px;
    border-radius: 4px;
    object-fit: cover;
    flex-shrink: 0;
    background: #334155;
}}

.room-btn .room-info {{
    flex: 1;
    min-width: 0;
}}

.room-btn .room-name {{
    display: block;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.room-btn .room-badge {{
    font-size: 10px;
    color: #22d3ee;
    margin-top: 2px;
    display: block;
}}

/* Navigation bar */
#nav-bar {{
    padding: 12px;
    border-top: 1px solid #334155;
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}}

#nav-bar button {{
    flex: 1;
    padding: 10px;
    border: 1px solid #475569;
    border-radius: 6px;
    background: #334155;
    color: #e2e8f0;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
}}

#nav-bar button:hover {{
    background: #475569;
    border-color: #64748b;
}}

#nav-bar button:disabled {{
    opacity: 0.3;
    cursor: not-allowed;
}}

/* Panorama container */
#panorama-wrap {{
    flex: 1;
    position: relative;
    height: 100vh;
}}

#panorama {{
    width: 100%;
    height: 100%;
}}

/* Toggle button */
#sidebar-toggle {{
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 200;
    width: 40px;
    height: 40px;
    border-radius: 8px;
    border: 1px solid #475569;
    background: rgba(30, 41, 59, 0.9);
    color: #e2e8f0;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    backdrop-filter: blur(8px);
}}

#sidebar-toggle:hover {{
    background: rgba(51, 65, 85, 0.95);
}}

/* Room title overlay */
#room-title {{
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 150;
    background: rgba(15, 23, 42, 0.85);
    color: #f1f5f9;
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
    backdrop-filter: blur(8px);
    border: 1px solid #334155;
    pointer-events: none;
    white-space: nowrap;
}}

/* Keyboard hint */
#key-hint {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    z-index: 150;
    font-size: 11px;
    color: #64748b;
    pointer-events: none;
}}

/* Responsive */
@media (max-width: 768px) {{
    #sidebar {{
        position: absolute;
        left: 0;
        top: 0;
        width: 280px;
        min-width: 280px;
        box-shadow: 4px 0 24px rgba(0,0,0,0.5);
    }}
    #sidebar.collapsed {{
        transform: translateX(-280px);
    }}
}}

/* Override Pannellum controls styling */
.pnlm-controls-container {{
    top: 12px !important;
    right: 12px !important;
}}

/* File protocol warning overlay */
#file-warning {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 9999;
    background: #0f172a;
    color: #e2e8f0;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 40px;
}}
#file-warning.show {{ display: flex; }}
#file-warning h2 {{ font-size: 24px; margin-bottom: 16px; color: #38bdf8; }}
#file-warning p {{ font-size: 15px; color: #94a3b8; max-width: 520px; margin-bottom: 12px; line-height: 1.6; }}
#file-warning code {{
    display: block;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 16px 24px;
    font-size: 14px;
    color: #22d3ee;
    margin: 16px 0;
    cursor: pointer;
    user-select: all;
    word-break: break-all;
}}
#file-warning .hint {{ font-size: 12px; color: #64748b; margin-top: 4px; }}

#file-warning .fw-logo {{
    margin-bottom: 8px;
}}

#file-warning .fw-logo svg {{
    width: 80px;
    height: 80px;
}}

#file-warning .fw-app-name {{
    font-size: 22px;
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 4px;
    letter-spacing: 1px;
}}

#file-warning .fw-tour-name {{
    font-size: 16px;
    color: #f1f5f9;
    margin-bottom: 20px;
}}

#file-warning .fw-subtitle {{
    font-size: 14px;
    color: #94a3b8;
    max-width: 560px;
    margin-bottom: 8px;
    line-height: 1.6;
}}

#file-warning .fw-divider {{
    width: 60px;
    height: 2px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    border-radius: 1px;
    margin: 20px 0;
}}

#file-warning .platform-sections {{
    display: flex;
    gap: 20px;
    max-width: 720px;
    width: 100%;
    margin-top: 8px;
}}

#file-warning .platform-box {{
    flex: 1;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 24px;
    text-align: left;
    transition: border-color 0.2s ease;
}}

#file-warning .platform-box:hover {{
    border-color: #475569;
}}

#file-warning .platform-box h3 {{
    font-size: 17px;
    color: #f1f5f9;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 12px;
    border-bottom: 1px solid #334155;
}}

#file-warning .platform-box .platform-icon {{
    font-size: 22px;
}}

#file-warning .platform-box .method {{
    margin-bottom: 16px;
}}

#file-warning .platform-box .method:last-child {{
    margin-bottom: 0;
}}

#file-warning .platform-box .method-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748b;
    margin-bottom: 6px;
    font-weight: 600;
}}

#file-warning .platform-box .method-action {{
    font-size: 14px;
    color: #e2e8f0;
    line-height: 1.5;
}}

#file-warning .platform-box .method-action strong {{
    color: #22d3ee;
}}

#file-warning .platform-box code {{
    display: block;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 12px;
    color: #22d3ee;
    margin: 8px 0 0 0;
    cursor: pointer;
    user-select: all;
    word-break: break-all;
    transition: all 0.15s ease;
}}

#file-warning .platform-box code:hover {{
    background: #334155;
    border-color: #38bdf8;
}}

#file-warning .url-note {{
    font-size: 14px;
    color: #94a3b8;
    margin-top: 24px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 24px;
}}

#file-warning .url-note strong {{
    color: #22d3ee;
}}

#file-warning .fw-footer {{
    margin-top: 32px;
    padding-top: 20px;
    border-top: 1px solid #1e293b;
    text-align: center;
}}

#file-warning .fw-footer .fw-credit {{
    font-size: 12px;
    color: #475569;
    margin-bottom: 6px;
}}

#file-warning .fw-footer a {{
    color: #38bdf8;
    text-decoration: none;
    font-size: 12px;
}}

#file-warning .fw-footer a:hover {{
    color: #22d3ee;
    text-decoration: underline;
}}

@media (max-width: 700px) {{
    #file-warning .platform-sections {{
        flex-direction: column;
    }}
    #file-warning {{ padding: 24px; }}
}}
</style>
</head>
<body>

<div id="file-warning">
    <div class="fw-logo">
        <svg viewBox="0 0 512 512" width="80" height="80">
            <defs>
                <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#0f172a"/><stop offset="100%" style="stop-color:#1e293b"/></linearGradient>
                <linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#38bdf8"/><stop offset="100%" style="stop-color:#818cf8"/></linearGradient>
                <linearGradient id="arrow" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#22d3ee"/><stop offset="100%" style="stop-color:#3b82f6"/></linearGradient>
                <linearGradient id="house" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#f472b6"/><stop offset="100%" style="stop-color:#c084fc"/></linearGradient>
            </defs>
            <circle cx="256" cy="256" r="250" fill="url(#bg)" stroke="#334155" stroke-width="4"/>
            <ellipse cx="256" cy="240" rx="155" ry="55" fill="none" stroke="url(#ring)" stroke-width="10" stroke-linecap="round" stroke-dasharray="320 60" opacity="0.9"/>
            <ellipse cx="256" cy="240" rx="155" ry="55" fill="none" stroke="url(#ring)" stroke-width="7" stroke-linecap="round" stroke-dasharray="280 100" opacity="0.5" transform="rotate(60,256,240)"/>
            <ellipse cx="256" cy="240" rx="155" ry="55" fill="none" stroke="url(#ring)" stroke-width="7" stroke-linecap="round" stroke-dasharray="250 130" opacity="0.35" transform="rotate(-60,256,240)"/>
            <g transform="translate(256,225)"><polygon points="0,-52 -48,-10 48,-10" fill="url(#house)" opacity="0.95"/><rect x="-35" y="-10" width="70" height="50" rx="3" fill="url(#house)" opacity="0.85"/><rect x="-10" y="10" width="20" height="30" rx="2" fill="#0f172a" opacity="0.7"/><rect x="-30" y="0" width="14" height="12" rx="2" fill="#22d3ee" opacity="0.6"/><rect x="16" y="0" width="14" height="12" rx="2" fill="#22d3ee" opacity="0.6"/></g>
            <g transform="translate(256,340)"><line x1="0" y1="-15" x2="0" y2="25" stroke="url(#arrow)" stroke-width="10" stroke-linecap="round"/><polyline points="-18,8 0,28 18,8" fill="none" stroke="url(#arrow)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/><line x1="-28" y1="38" x2="28" y2="38" stroke="url(#arrow)" stroke-width="8" stroke-linecap="round"/></g>
            <text x="256" y="440" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="52" fill="#38bdf8" letter-spacing="4">360</text>
        </svg>
    </div>

    <div class="fw-app-name">360 MLS Downloader</div>
    <div class="fw-tour-name">{_escape_html(tour_name)}</div>

    <p class="fw-subtitle">This 360° tour viewer needs a local web server to display panoramas.<br>Choose your platform below to get started.</p>

    <div class="fw-divider"></div>

    <div class="platform-sections">
        <div class="platform-box">
            <h3><span class="platform-icon">&#63743;</span> Mac</h3>

            <div class="method">
                <div class="method-label">Option 1 — One Click</div>
                <div class="method-action">Double-click <strong>"Open Tour Viewer.command"</strong> in this folder</div>
            </div>

            <div class="method">
                <div class="method-label">Option 2 — Terminal</div>
                <div class="method-action">Copy and paste into Terminal:</div>
                <code id="mac-cmd" onclick="navigator.clipboard.writeText(this.textContent).then(function(){{document.getElementById('mac-copy').textContent='Copied!'}})">python3 -m http.server 8360</code>
                <p class="hint" id="mac-copy">Click to copy</p>
            </div>
        </div>

        <div class="platform-box">
            <h3><span class="platform-icon">&#8862;</span> Windows</h3>

            <div class="method">
                <div class="method-label">Option 1 — One Click</div>
                <div class="method-action">Double-click <strong>"Open Tour Viewer.bat"</strong> in this folder</div>
            </div>

            <div class="method">
                <div class="method-label">Option 2 — Command Prompt</div>
                <div class="method-action">Copy and paste into CMD or PowerShell:</div>
                <code id="win-cmd" onclick="navigator.clipboard.writeText(this.textContent).then(function(){{document.getElementById('win-copy').textContent='Copied!'}})">python -m http.server 8360</code>
                <p class="hint" id="win-copy">Click to copy</p>
            </div>
        </div>
    </div>

    <p class="url-note">Then open: <strong>http://localhost:8360/tour-viewer.html</strong></p>

    <div class="fw-footer">
        <div class="fw-credit">PRHack | CyberSpartan77</div>
        <a href="https://github.com/fjimenez77/360-MLS-Downloader" target="_blank">github.com/fjimenez77/360-MLS-Downloader</a>
    </div>
</div>

<div id="sidebar">
    <div id="sidebar-header">
        <h1>{_escape_html(tour_name)}</h1>
        <div class="address">{_escape_html(address)}</div>
        <div class="photographer">{_escape_html(photographer)}</div>
        <div class="room-count">{room_count} rooms</div>
    </div>
    <div id="room-list"></div>
    <div id="nav-bar">
        <button id="btn-prev" onclick="prevRoom()">&#9664; Previous</button>
        <button id="btn-next" onclick="nextRoom()">Next &#9654;</button>
    </div>
</div>

<div id="panorama-wrap">
    <button id="sidebar-toggle" onclick="toggleSidebar()">&#9776;</button>
    <div id="panorama"></div>
    <div id="room-title"></div>
    <div id="key-hint">&#8592; &#8594; arrow keys to navigate rooms</div>
</div>

<script>
{pannellum_js}
</script>
<script>
// Detect file:// protocol and show warning
if (window.location.protocol === 'file:') {{
    document.getElementById('file-warning').classList.add('show');
    // Set the commands with the correct directory
    var path = decodeURIComponent(window.location.pathname);
    var dir = path.substring(0, path.lastIndexOf('/'));
    document.getElementById('mac-cmd').textContent =
        'cd "' + dir + '" && python3 -m http.server 8360';
    // Windows path conversion (swap / to \, remove leading /)
    var winDir = dir.replace(/\\//g, '\\\\');
    if (winDir.startsWith('\\\\')) winDir = winDir.substring(1);
    document.getElementById('win-cmd').textContent =
        'cd /d "' + winDir + '" && python -m http.server 8360';
}}
</script>
<script>
(function() {{
    if (window.location.protocol === 'file:') return; // Don't initialize if file://

    var ROOMS = {rooms_json};
    var currentIndex = 0;

    // Build room buttons
    var roomList = document.getElementById('room-list');
    ROOMS.forEach(function(room, i) {{
        var btn = document.createElement('button');
        btn.className = 'room-btn' + (i === 0 ? ' active' : '');
        btn.setAttribute('data-index', i);

        var thumb = '';
        if (room.preview) {{
            thumb = '<img class="room-thumb" src="' + room.preview + '" alt="" loading="lazy">';
        }} else {{
            thumb = '<div class="room-thumb"></div>';
        }}

        var badge = room.has_enhanced ? '<span class="room-badge">AI Enhanced</span>' : '';

        btn.innerHTML = thumb +
            '<div class="room-info">' +
                '<span class="room-name">' + room.index + '. ' + room.name + '</span>' +
                badge +
            '</div>';

        btn.addEventListener('click', function() {{
            goToRoom(i);
        }});

        roomList.appendChild(btn);
    }});

    // Initialize Pannellum
    var viewer = pannellum.viewer('panorama', {{
        default: {{
            firstScene: '{first_scene}',
            autoLoad: true,
            compass: false,
            showControls: true,
            type: 'equirectangular',
            hfov: 120,
            minHfov: 50,
            maxHfov: 140,
            autoRotate: -2,
            autoRotateInactivityDelay: 5000,
        }},
        scenes: {scenes_json}
    }});

    function goToRoom(index) {{
        if (index < 0 || index >= ROOMS.length) return;
        currentIndex = index;
        var sceneId = 'scene-' + ROOMS[index].index;
        viewer.loadScene(sceneId);
        updateUI();
    }}

    function updateUI() {{
        // Update active button
        var buttons = roomList.querySelectorAll('.room-btn');
        buttons.forEach(function(btn, i) {{
            btn.classList.toggle('active', i === currentIndex);
        }});

        // Scroll active button into view
        var activeBtn = roomList.querySelector('.room-btn.active');
        if (activeBtn) {{
            activeBtn.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
        }}

        // Update room title overlay
        var room = ROOMS[currentIndex];
        document.getElementById('room-title').textContent =
            room.index + '. ' + room.name + ' (' + (currentIndex + 1) + '/' + ROOMS.length + ')';

        // Update nav buttons
        document.getElementById('btn-prev').disabled = (currentIndex === 0);
        document.getElementById('btn-next').disabled = (currentIndex === ROOMS.length - 1);
    }}

    window.prevRoom = function() {{
        if (currentIndex > 0) goToRoom(currentIndex - 1);
    }};

    window.nextRoom = function() {{
        if (currentIndex < ROOMS.length - 1) goToRoom(currentIndex + 1);
    }};

    window.toggleSidebar = function() {{
        document.getElementById('sidebar').classList.toggle('collapsed');
    }};

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'ArrowLeft' && e.target === document.body) {{
            e.preventDefault();
            prevRoom();
        }} else if (e.key === 'ArrowRight' && e.target === document.body) {{
            e.preventDefault();
            nextRoom();
        }}
    }});

    // Listen for scene changes (from Pannellum hotspots etc)
    viewer.on('scenechange', function(sceneId) {{
        for (var i = 0; i < ROOMS.length; i++) {{
            if ('scene-' + ROOMS[i].index === sceneId) {{
                currentIndex = i;
                updateUI();
                break;
            }}
        }}
    }});

    // Initial UI state
    updateUI();
}})();
</script>
</body>
</html>'''


def _escape_html(text):
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))
