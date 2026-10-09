# YouTube Fetcher

## App
- **Name:** YouTube Fetcher
- **Version:** 2.1.1
- **Type:** Desktop (Windows) - Python 3.12+ / 3.14 + pywebview 6.x (Edge WebView2)
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (no framework, single `index.html`)
- **Database:** None (history stored as JSON in `{userData}/history.json`)
- **Settings:** JSON file at `{userData}/settings.json`
- **Binary:** `resources/yt-dlp.exe` + `resources/ffmpeg.exe` + `resources/qjs-x64.exe` / `qjs-x86.exe` (downloaded by `download_ytdlp.py`)
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
- Release notes format for checksums: body must contain `sha256 x64: <hex>` and `sha256 x86: <hex>` lines (app parses the one matching its architecture)

## Security Features (Mod 9, revised Mod 10)
- SHA-256 checksum verification on auto-update downloads (hard-fails if no checksum is listed — no silent fallback)
- Architecture-aware checksum parsing (release body `sha256 x64: <hex>` / `sha256 x86: <hex>` resolved per running architecture)
- TLS certificate verification enabled (removed `--no-check-certificates`)
- YouTube URL validation (only youtube.com/youtu.be URLs accepted)
- Cookie consent gate: browser cookies are read **only** when the user has granted access; consent is requested **only** when a video actually needs sign-in (no-cookie path tried first). Choice persisted in `settings.json` (`allow_cookies`) with a Settings toggle.
- Atomic JSON writes (temp file + rename) to prevent data corruption
- Path traversal prevention on file deletion (allow-list = default root, user-data dir, dirs written this session, configured save path)
- Rate limiting on concurrent downloads (max 10)
- Thread-safe update state management
- JavaScript injection prevention (`ensure_ascii=True` in JSON push)
- Downloaded binary hash verification in `download_ytdlp.py` (now includes pinned SHA-256 for the QuickJS runtime)
- Safe zip extraction (zip-slip prevention)

## Bundled JavaScript Runtime (Mod 10)
- yt-dlp 2026.x requires an external JS runtime to solve YouTube JS challenges.
- App bundles **QuickJS-ng** (`qjs.exe`), arch-matched: `resources/qjs-x64.exe` (x64 build) / `resources/qjs-x86.exe` (x86 build).
- `ytdlp_runner.get_js_runtime_args()` prefers bundled QuickJS, then system `deno`, then system `node`.
- `download_ytdlp.py` downloads both binaries with pinned SHA-256 (quickjs-ng publishes no checksums).
- Startup self-check (`backend.get_runtime_status()`) shows a clear dialog if no runtime is available.

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
| 10  | 2.1.1   | 2026-10-09 | **UX + dependency fixes.** (1) Custom download folder was silently ignored when outside `%USERPROFILE%` (other drives/UNC) — now any absolute user-picked folder is honored, invalid paths raise an explicit error (no silent fallback), and `delete_file` allow-list includes session dirs + saved path. (2) Bundled **QuickJS-ng v0.17.0** JS runtime per architecture so YouTube downloads work without Node.js/Python (`download_ytdlp.py` pins SHA-256; `ytdlp_runner.get_js_runtime_args()` selects bundled QuickJS → deno → node; startup self-check dialog). (3) Cookie consent redesigned: no-cookie fetch first, prompt only when a video needs sign-in, calm accurate copy with "Always allow / Just this once / Not now", choice persisted in `settings.json` (`allow_cookies`) + Settings toggle, backend consent gate. (4) `build.bat` now detects Inno Setup at `E:\AIprojects\AI Agent\InnoSetup\ISCC.exe`. |

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
- Inno Setup 6 (installer, at `E:\AIprojects\AI Agent\InnoSetup\ISCC.exe`)
- QuickJS-ng v0.17.0 (bundled JS runtime; downloaded by `download_ytdlp.py`)

## Development Workflow (mandatory)
- After every modification: build (both architectures), silently install the x64 build locally, and auto-launch it for the user to verify.
- **Never commit, tag, or create a GitHub release until the user explicitly approves.** Wait for verification first.
