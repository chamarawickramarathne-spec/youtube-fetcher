"""Download yt-dlp.exe and ffmpeg.exe into resources/ directory."""

import os
import sys
import urllib.request
import zipfile
import io
import shutil

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def download_file(url: str, dest: str) -> None:
    print(f"Downloading {os.path.basename(dest)}...")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"  -> {size_mb:.1f} MB")


def download_ytdlp() -> None:
    dest = os.path.join(RESOURCES_DIR, "yt-dlp.exe")
    if os.path.exists(dest):
        print("yt-dlp.exe already exists, skipping.")
        return
    download_file(YTDLP_URL, dest)
    print("yt-dlp.exe downloaded.")


def download_ffmpeg() -> None:
    dest = os.path.join(RESOURCES_DIR, "ffmpeg.exe")
    if os.path.exists(dest):
        print("ffmpeg.exe already exists, skipping.")
        return
    print("Downloading ffmpeg essentials (this may take a moment)...")
    tmp_zip = os.path.join(RESOURCES_DIR, "_ffmpeg_tmp.zip")
    download_file(FFMPEG_URL, tmp_zip)
    print("Extracting ffmpeg.exe...")
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        exe_names = [n for n in zf.namelist() if n.endswith("ffmpeg.exe")]
        if not exe_names:
            print("ERROR: ffmpeg.exe not found in zip archive.")
            sys.exit(1)
        with zf.open(exe_names[0]) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
    os.remove(tmp_zip)
    print("ffmpeg.exe extracted.")


if __name__ == "__main__":
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    download_ytdlp()
    download_ffmpeg()
    print("All resources ready.")
