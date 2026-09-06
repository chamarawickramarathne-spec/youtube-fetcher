# YouTube Fetcher

## App
- **Name:** YouTube Fetcher
- **Version:** 2.1.0
- **Type:** Desktop (Windows) - Python 3.12+ / 3.14 + pywebview 6.x (Edge WebView2)
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (no framework, single `index.html`)
- **Database:** None (history stored as JSON in `{userData}/history.json`)
- **Settings:** JSON file at `{userData}/settings.json`
- **Binary:** `resources/yt-dlp.exe` + `resources/ffmpeg.exe` (downloaded by `download_ytdlp.py`)
- **Icon:** `media/icon.ico` (multi-size) + `media/icon.png`
- **Architectures:** x64 (Python 3.14) + x86 (Python 3.12)

## Architecture
- `main.py` — pywebview window lifecycle, API registration
- `backend.py` — pywebview API bridge (composes modules, exposes JS API)
- `storage.py` — atomic JSON I/O, history, settings, safe file operations
- `ytdlp_runner.py` — yt-dlp subprocess execution, URL validation, bot-detection bypass
- `updater.py` — auto-update system with SHA-256 checksum verification
- `downloader.py` — download execution, rate limiting, progress tracking
- `index.html` — complete UI (inline CSS + JS, no build step)
- `download_ytdlp.py` — resource bootstrap script with hash verification
- `youtube_fetcher-x64.spec` — PyInstaller config (64-bit)
- `youtube_fetcher-x86.spec` — PyInstaller config (32-bit)
- `installer-x64.iss` — Inno Setup installer script (64-bit)
- `installer-x86.iss` — Inno Setup installer script (32-bit)
- `build.bat` — build automation (dual-architecture)

## Build
- Dev: `python main.py` (or `python main.py --debug`)
- Build: `build.bat` (builds both x64 and x86)
- Build requires: Python 3.14 (x64) + Python 3.12 (x86)
- Output structure:
  ```
  dist-x64/youtube-fetcher.exe
  dist-x86/youtube-fetcher.exe
  release/x64/youtube-fetcher-setup-x64.exe
  release/x86/youtube-fetcher-setup-x86.exe
  ```
- Update feature: checks GitHub API, downloads arch-specific `-setup-x64.exe` or `-setup-x86.exe`, verifies SHA-256 checksum, launches installer

## Security Features (Mod 9)
- SHA-256 checksum verification on auto-update downloads (hard-fails if no checksum is listed — no silent fallback)
- TLS certificate verification enabled (removed `--no-check-certificates`)
- YouTube URL validation (only youtube.com/youtu.be URLs accepted)
- Cookie access consent dialog before browser cookie extraction
- Atomic JSON writes (temp file + rename) to prevent data corruption
- Path traversal prevention on file deletion
- Rate limiting on concurrent downloads (max 10)
- Thread-safe update state management
- JavaScript injection prevention (`ensure_ascii=True` in JSON push)
- Downloaded binary hash verification in `download_ytdlp.py`
- Safe zip extraction (zip-slip prevention)

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
| 8   | 2.0.1   | 2026-08-18 | Fixed Settings > Browse button opening file picker instead of folder picker (dialog type 0 -> 20). |
| 9   | 2.1.0   | 2026-09-06 | **Security audit + dual-arch build.** Modular backend (5 modules). 22 security/bug fixes: SHA-256 update verification (hard-fails if no checksum — no silent fallback), TLS cert validation, cookie consent dialog, YouTube URL validation, atomic JSON writes, path traversal prevention, rate limiting, thread-safe update state, JS injection prevention, binary hash verification, zip-slip fix. Dual-architecture builds (x64 + x86). Architecture-specific installers and auto-updater. Removed obsolete single-arch `youtube_fetcher.spec` and `installer.iss`. |

## Update Feature
- Publish provider: GitHub (`chamarawickramarathne-spec/youtube-fetcher`).
- Python auto-update: checks GitHub API `/releases/latest`, compares versions, downloads arch-specific installer, verifies SHA-256 checksum, launches installer.
- Architecture detection: auto-selects `-setup-x64.exe` or `-setup-x86.exe` based on running Python architecture.
- To publish a new version:
  1. Bump `_app_version` in `backend.py` (`Backend.get_app_version()`).
  2. Run `build.bat` (builds both architectures).
  3. `gh release create v<version> release/x64/youtube-fetcher-setup-x64.exe release/x86/youtube-fetcher-setup-x86.exe --title "v<version>" --notes "Release notes"`.
- Verify with:
  - `curl -sL -H "Accept: application/json" https://github.com/chamarawickramarathne-spec/youtube-fetcher/releases/latest` -> JSON with `tag_name`.

## Dependencies
- Python 3.14 (x64 build) or Python 3.12 (x86 build)
- pywebview 6.x (Edge WebView2)
- pyperclip (clipboard)
- PyInstaller 6.x (build)
- Inno Setup 6 (installer)
