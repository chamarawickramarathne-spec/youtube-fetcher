"""Download yt-dlp.exe and ffmpeg.exe into resources/ directory (H2: hash verification)."""

import hashlib
import os
import sys
import urllib.request
import zipfile
import shutil


RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: str) -> None:
    print(f"Downloading {os.path.basename(dest)}...")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"  -> {size_mb:.1f} MB")


def verify_against_known(path: str, known_hash: str | None) -> bool:
    if not known_hash:
        print(f"  WARNING: No known hash for {os.path.basename(path)} — skipping verification")
        return True
    actual = sha256_file(path)
    if actual.lower() == known_hash.lower():
        print(f"  SHA-256 verified: {actual[:16]}...")
        return True
    print(f"  ERROR: Hash mismatch! Expected {known_hash[:16]}... got {actual[:16]}...")
    return False


def download_ytdlp(known_hash: str | None = None) -> None:
    dest = os.path.join(RESOURCES_DIR, "yt-dlp.exe")
    if os.path.exists(dest):
        if verify_against_known(dest, known_hash):
            print("yt-dlp.exe exists and verified, skipping.")
            return
        print("yt-dlp.exe exists but hash mismatch — re-downloading...")
        os.remove(dest)
    download_file(YTDLP_URL, dest)
    if not verify_against_known(dest, known_hash):
        print("WARNING: yt-dlp.exe hash could not be verified!")
    else:
        print("yt-dlp.exe downloaded and verified.")


def download_ffmpeg(known_hash: str | None = None) -> None:
    dest = os.path.join(RESOURCES_DIR, "ffmpeg.exe")
    if os.path.exists(dest):
        if verify_against_known(dest, known_hash):
            print("ffmpeg.exe exists and verified, skipping.")
            return
        print("ffmpeg.exe exists but hash mismatch — re-downloading...")
        os.remove(dest)
    print("Downloading ffmpeg essentials (this may take a moment)...")
    tmp_zip = os.path.join(RESOURCES_DIR, "_ffmpeg_tmp.zip")
    download_file(FFMPEG_URL, tmp_zip)
    print("Extracting ffmpeg.exe...")
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        exe_names = [
            n for n in zf.namelist()
            if n.endswith("ffmpeg.exe") and "/" not in n.split("ffmpeg.exe")[0]
        ]
        if not exe_names:
            all_matches = [n for n in zf.namelist() if n.endswith("ffmpeg.exe")]
            if all_matches:
                exe_names = [all_matches[-1]]
        if not exe_names:
            print("ERROR: ffmpeg.exe not found in zip archive.")
            sys.exit(1)
        with zf.open(exe_names[0]) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
    os.remove(tmp_zip)
    if not verify_against_known(dest, known_hash):
        print("WARNING: ffmpeg.exe hash could not be verified!")
    else:
        print("ffmpeg.exe extracted and verified.")


if __name__ == "__main__":
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    ytdlp_hash = os.environ.get("YTDLP_SHA256")
    ffmpeg_hash = os.environ.get("FFMPEG_SHA256")
    download_ytdlp(ytdlp_hash)
    download_ffmpeg(ffmpeg_hash)
    print("All resources ready.")
