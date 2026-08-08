# YouTube Fetcher

## App
- **Name:** YouTube Fetcher
- **Version:** 1.0.0
- **Type:** Desktop (Windows) - Electron + React + TypeScript
- **Database:** None (history stored as JSON in userData/history.json)
- **Binary:** `resources/yt-dlp.exe` + `resources/ffmpeg.exe` (downloaded by `scripts/download-ytdlp.js` on install)

## Build
- Installer: `npm run build:win` -> `release/youtube-fetcher-<version>-setup.exe`
- Update feature uses electron-updater + GitHub releases.

## Modification History

| Mod | Version | Date       | Details |
|-----|---------|------------|---------|
| 1   | 1.0.0   | 2026-08-08 | Initial app with auto-update feature via electron-updater. Created GitHub repo (chamarawickramarathne-spec/youtube-fetcher, public), publish config in electron-builder.yml, auto-check on startup + manual check/download/install in Settings, header update badge. Published GitHub release v1.0.0. |

## Update Feature
- Publish provider: GitHub (`chamarawickramarathne-spec/youtube-fetcher`).
- To publish a new version:
  1. Bump `version` in package.json.
  2. `$env:GH_TOKEN = gh auth token`
  3. `npm run build:win -- --publish always`
  4. Git tag `v<version>` and push.
