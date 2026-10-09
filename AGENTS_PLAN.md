# AGENTS_PLAN.md — YouTube Fetcher

## Goal
Ship v2.1.4 (installer self-kill fix), carrying the Mod 11 installer upgrade fix and the
v2.1.1 UX/dependency fixes. **Release is withheld until the user explicitly approves.**

## Completed — v2.1.4 (Mod 13)
- Fix: the Mod 11 force-close used `taskkill /T`, which killed the installer itself
  because the in-app updater launches the installer as a **child** of the running app.
  Changed both installers to `taskkill /F /IM youtube-fetcher.exe` (no `/T`).

## Completed — v2.1.3 (Mod 12, test release)
- Version bump only (no functional change) to publish the Mod 11 installer fix and
  exercise the update flow: installed 2.1.2 detects 2.1.3, downloads the arch-matched
  installer, verifies SHA-256, installer closes the running app and replaces it.
- Local install step intentionally skipped so a running 2.1.2 can test updating to 2.1.3.

## Completed — v2.1.2 (Mod 11)
- **Installer upgrade fix:** installing over a running app failed because Inno's Restart
  Manager could not close the PyInstaller process (`DeleteFile failed; code 5`), leaving
  the old exe. Added an Inno `[Code]` `PrepareToInstall` step to `installer-x64.iss` and
  `installer-x86.iss` that force-closes `youtube-fetcher.exe`
  (`taskkill /F /T /IM youtube-fetcher.exe`) before file copying; added
  `CloseApplications=no` + `RestartApplications=no` to suppress the broken Restart
  Manager prompt. Also fixes the in-app updater path.
- Version bumped to **2.1.2** (`backend.py`, both `.iss`).
- Verified: with the app running, a silent install closed it, replaced the exe
  (timestamp updated, exit 0, no prompt, log line "Closing any running ... instance").
- Docs updated: `AGENTS.md` (Mod 11), this plan, `medial_support.txt`.

## Completed — v2.1.1 (Mod 10)
- Custom download folder honored on any drive (no silent fallback); delete allow-list
  includes session dirs + saved path.
- Bundled QuickJS-ng v0.17.0 JS runtime per architecture (pinned SHA-256); runtime
  selection QuickJS -> deno -> node; startup self-check dialog.
- Cookie consent redesigned: no prompt for public videos; asks only when sign-in is
  required; choice remembered (`allow_cookies` + Settings toggle); backend consent gate.
- `build.bat` finds Inno Setup at its installed location.

## Pending
- User verification of v2.1.2 (install while app running).
- On explicit user approval only: commit, tag `v2.1.2`, `gh release create` both
  installers with `sha256 x64:` / `sha256 x86:` notes; verify latest release.

## Notes / Decisions
- Runtime choice: QuickJS-ng — only runtime with both Windows x86/x64 builds at
  negligible size (Deno/Bun have no 32-bit Windows build; Node is ~80 MB/arch).
- `backend.save_settings` merges with existing values instead of clobbering.
- Installer closes the running app itself (explicit, logged) rather than relying on
  Restart Manager, which could not terminate the PyInstaller onefile process.
