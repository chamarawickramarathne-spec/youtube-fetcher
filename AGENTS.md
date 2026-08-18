# YouTube Fetcher

## App
- **Name:** YouTube Fetcher
- **Version:** 2.0.0
- **Type:** Desktop (Windows) - Python 3.12 + pywebview 6.x (Edge WebView2)
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (no framework, single `index.html`)
- **Database:** None (history stored as JSON in `{userData}/history.json`)
- **Settings:** JSON file at `{userData}/settings.json`
- **Binary:** `resources/yt-dlp.exe` + `resources/ffmpeg.exe` (downloaded by `download_ytdlp.py`)
- **Icon:** `media/icon.ico` (multi-size) + `media/icon.png`

## Architecture
- `main.py` — pywebview window lifecycle, API registration
- `backend.py` — yt-dlp execution, history, settings, file ops, auto-update (all exposed via `js_api`)
- `index.html` — complete UI (inline CSS + JS, no build step)
- `download_ytdlp.py` — resource bootstrap script
- `youtube_fetcher.spec` — PyInstaller config (single .exe)
- `installer.iss` — Inno Setup installer script
- `build.bat` — build automation

## Build
- Dev: `python main.py` (or `python main.py --debug`)
- Build: `build.bat` (PyInstaller + Inno Setup)
- Output: `release/youtube-fetcher-setup.exe` (~83 MB)
- Executable: `dist/youtube-fetcher.exe` (~81.5 MB)
- Update feature: checks GitHub API for latest release, downloads setup.exe, launches installer

## Modification History

| Mod | Version | Date       | Details |
|-----|---------|------------|---------|
| 1   | 1.0.0   | 2026-08-08 | Initial Electron + React + TypeScript app. GitHub repo, auto-update, all features. |
| 2   | 1.0.0   | 2026-08-08 | Added unique app icon via `scripts/generate-icon.ps1`. Published GitHub release v1.0.0. |
| 3   | 1.0.0   | 2026-08-08 | Fixed "Cannot parse releases feed / HttpError 406" — duplicate draft releases. |
| 4   | 1.0.0   | 2026-08-08 | Header UI: unified update button with version display. |
| 5   | 1.0.0   | 2026-08-08 | Fixed broken npm, rebuilt installer. |
| 6   | 1.0.1   | 2026-08-08 | Released v1.0.1, published to GitHub with electron-updater. |
| 7   | 2.0.0   | 2026-08-18 | **Full rewrite**: Electron+React -> Python+pywebview+vanilla JS. Single-file frontend (`index.html`). PyInstaller single .exe. Inno Setup installer. Same UI/UX, all features preserved. Installer size: ~83 MB (was ~450 MB). |

## Update Feature
- Publish provider: GitHub (`chamarawickramarathne-spec/youtube-fetcher`).
- Python auto-update: checks GitHub API `/releases/latest`, compares versions, downloads `-setup.exe` asset, launches installer.
- To publish a new version:
  1. Bump `_app_version` in `backend.py`.
  2. Run `build.bat`.
  3. `gh release create v<version> release/youtube-fetcher-setup.exe --title "v<version>" --notes "Release notes"`.
- Verify with:
  - `curl -sL -H "Accept: application/json" https://github.com/chamarawickramarathne-spec/youtube-fetcher/releases/latest` -> JSON with `tag_name`.

## Dependencies
- Python 3.12+
- pywebview 6.x (Edge WebView2)
- pyperclip (clipboard)
- PyInstaller (build)
- Inno Setup 6 (installer)
