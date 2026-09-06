# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — x64 (64-bit AMD64)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('resources/yt-dlp.exe', 'resources'),
        ('resources/ffmpeg.exe', 'resources'),
    ],
    datas=[
        ('index.html', '.'),
        ('media/icon.ico', 'media'),
    ],
    hiddenimports=['storage', 'ytdlp_runner', 'updater', 'downloader'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='youtube-fetcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x64',
    codesign_identity=None,
    entitlements_file=None,
    icon='media/icon.ico',
    version_info=None,
)
