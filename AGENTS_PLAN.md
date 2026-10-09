# AGENTS_PLAN.md — YouTube Fetcher v2.1.1

## Goal
Release v2.1.1 fixing three user-facing issues plus build tooling, then verify
locally before releasing. **Release is withheld until the user explicitly approves.**

## Completed
- **Fix 1 — Download folder ignored:** `downloader.py::_get_downloads_dir` now honors any
  absolute user-picked folder (any drive/UNC); invalid paths raise (no silent fallback).
  `delete_file` allows session-written dirs + saved settings path. `index.html` persists
  `save_path` to backend `settings.json` and loads it on init.
- **Fix 2 — Missing JS runtime:** bundled QuickJS-ng v0.17.0 arch-matched
  (`resources/qjs-x64.exe`, `resources/qjs-x86.exe`) with pinned SHA-256 in
  `download_ytdlp.py`; both specs bundle the matching binary;
  `ytdlp_runner.get_js_runtime_args()` selects bundled QuickJS → deno → node; startup
  self-check (`backend.get_runtime_status()`) surfaces a clear dialog if missing.
- **Fix 3 — Cookie consent on every fetch:** no-cookie fetch tried first; prompt only when
  a video truly needs sign-in; new accurate copy with "Always allow / Just this once /
  Not now"; `allow_cookies` persisted in `settings.json` + Settings toggle; backend
  consent gate (`fetch_json(..., allow_cookies)`), `grant_cookie_access()`.
- **Fix 4 — Build tooling:** `build.bat` also looks for Inno Setup at
  `E:\AIprojects\AI Agent\InnoSetup\ISCC.exe`.
- Version bumped to **2.1.1** (`backend.py`, `installer-x64.iss`, `installer-x86.iss`).
- Docs updated: `AGENTS.md` (Mod 10, runtime section, workflow rule), this plan,
  `medial_support.txt`.

## Pending
- Build both architectures (`build.bat`).
- Silently install x64 + auto-launch; user verification of all three fixes.
- On explicit user approval only: commit, tag `v2.1.1`, `gh release create` both
  installers with `sha256 x64:` / `sha256 x86:` notes; verify latest release.

## Notes / Decisions
- JS runtime choice: QuickJS-ng (option A) — the only runtime with both Windows x86/x64
  builds at negligible size (Deno/Bun have no 32-bit Windows build; Node is ~80 MB/arch).
- Settings writes merge with existing values (`backend.save_settings`) instead of
  clobbering, so saving one key no longer wipes others.
