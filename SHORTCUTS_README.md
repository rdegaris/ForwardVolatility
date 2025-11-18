# Desktop Shortcuts Setup

## Quick Start

**Double-click `create_shortcuts.vbs`** to create desktop shortcuts with icons.

This will create two shortcuts on your desktop:
- 🔵 **Forward Vol - Daily Scan** - Runs all scans + IB positions sync
- 🟢 **Forward Vol - Scans Only** - Runs scans only (no IB connection needed)

## What the shortcuts do:

1. Run the Python scanner
2. Copy results to the web project
3. Commit and push to GitHub
4. Auto-deploy to your website (~2 minutes)

## Manual Setup (if VBS doesn't work)

### Option 1: Pin to Taskbar
1. Right-click `run_daily.bat`
2. Select "Pin to taskbar"

### Option 2: Create shortcut manually
1. Right-click on desktop → New → Shortcut
2. Browse to `run_daily.bat` or `run_scans_only.bat`
3. Name it (e.g., "Forward Vol Scanner")
4. Right-click shortcut → Properties → Change Icon
5. Browse to: `C:\Windows\System32\shell32.dll`
6. Pick an icon you like (176 or 177 are chart icons)

## Icons Available

If you want different icons, edit `create_shortcuts.vbs` and change the number:
- 176, 177 = Chart/graph icons
- 238 = Settings gear
- 166 = Play button
- 147 = Globe/web

Or use custom .ico files by changing:
```vbscript
DailyLink.IconLocation = "C:\path\to\your\icon.ico"
```
