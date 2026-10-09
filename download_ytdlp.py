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

# QuickJS-ng JS runtime (required by yt-dlp for YouTube JS challenges).
# Pinned version + SHA-256 (quickjs-ng publishes no official checksums).
QJS_VERSION = "0.17.0"
QJS_BASE_URL = f"https://github.com/quickjs-ng/quickjs/releases/download/v{QJS_VERSION}"
QJS_TARGETS = {
    "qjs-x64.exe": (
        f"{QJS_BASE_URL}/qjs-windows-x86_64.exe",
        "2aeabf0092c3262d6b2609824418f7dd7ed1f1df939f73b2b15645230cac0d77",
    ),
    "qjs-x86.exe": (
        f"{QJS_BASE_URL}/qjs-windows-x86.exe",
        "dedc4dd8da20234d206c433a706336fede47a14e75c690cb607f81aa9c9c71be",
    ),
}


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


def download_js_runtimes() -> None:
    for filename, (url, known_hash) in QJS_TARGETS.items():
        dest = os.path.join(RESOURCES_DIR, filename)
        if os.path.exists(dest):
            if verify_against_known(dest, known_hash):
                print(f"{filename} exists and verified, skipping.")
                continue
            print(f"{filename} exists but hash mismatch — re-downloading...")
            os.remove(dest)
        download_file(url, dest)
        if not verify_against_known(dest, known_hash):
            print(f"ERROR: {filename} hash could not be verified!")
            sys.exit(1)
        print(f"{filename} downloaded and verified.")


if __name__ == "__main__":
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    ytdlp_hash = os.environ.get("YTDLP_SHA256")
    ffmpeg_hash = os.environ.get("FFMPEG_SHA256")
    download_ytdlp(ytdlp_hash)
    download_ffmpeg(ffmpeg_hash)
    download_js_runtimes()
    print("All resources ready.")
