"""yt-dlp subprocess execution with URL validation and bot-detection bypass."""

import json
import os
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed


FETCH_TIMEOUT = 30
COOKIE_BROWSERS = ["edge", "chrome", "brave", "vivaldi", "firefox"]
EXTRACTOR_BYPASS_ATTEMPTS = [
    ("web+mweb client", ["--extractor-args", "youtube:player_client=web,mweb"]),
    ("android client", ["--extractor-args", "youtube:player_client=android"]),
    ("ios client", ["--extractor-args", "youtube:player_client=ios"]),
    ("tv client", ["--extractor-args", "youtube:player_client=tv"]),
]

_YT_DOMAINS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "music.youtube.com",
}


# ── URL validation (H1) ──

def is_valid_youtube_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except (ValueError, AttributeError):
        return False
    if parsed.scheme not in ("http", "https", ""):
        return False
    host = parsed.hostname or ""
    if host in _YT_DOMAINS:
        return True
    if host.endswith(".youtube.com"):
        return True
    return False


# ── yt-dlp path resolution ──

def get_ytdlp_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
        candidate = os.path.join(base, "resources", "yt-dlp.exe")
        if os.path.exists(candidate):
            return candidate
    dev = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "yt-dlp.exe")
    if os.path.exists(dev):
        return dev
    return "yt-dlp"


def get_ffmpeg_dir() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
        candidate = os.path.join(base, "resources")
        if os.path.exists(os.path.join(candidate, "ffmpeg.exe")):
            return candidate
    dev_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
    if os.path.exists(os.path.join(dev_dir, "ffmpeg.exe")):
        return dev_dir
    return ""


# ── Single yt-dlp run (C2: removed --no-check-certificates) ──

def run_ytdlp_once(url: str, extra_args: list[str] | None = None) -> dict:
    args = [
        get_ytdlp_path(),
        "--dump-single-json", "--no-download", "--no-warnings",
        "--no-playlist", "--js-runtimes", "node",
    ]
    if extra_args:
        args.extend(extra_args)
    args.append(url)

    proc = None
    try:
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stdout, stderr = proc.communicate(timeout=FETCH_TIMEOUT)
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        combined = (stdout_str + "\n" + stderr_str).strip()

        if proc.returncode != 0:
            return {"success": False, "error": combined or f"exit code {proc.returncode}"}
        try:
            return {"success": True, "data": json.loads(stdout_str)}
        except json.JSONDecodeError:
            return {"success": False, "error": combined or "Failed to parse yt-dlp JSON"}
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.wait()
        return {"success": False, "error": "Fetch timed out after 30 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Bot detection (M3: precise matching) ──

def is_bot_detection(error: str | None) -> bool:
    if not error:
        return False
    lower = error.lower()
    return "sign in to confirm" in lower or "bot detection" in lower


# ── Multi-strategy fetch with cookie bypass ──

def fetch_json(url: str, working_cookie_browser: str | None) -> tuple[dict, str | None]:
    if working_cookie_browser not in (None, ""):
        result = run_ytdlp_once(url, ["--cookies-from-browser", working_cookie_browser])
        if result["success"]:
            return result["data"], working_cookie_browser

    no_cookie = run_ytdlp_once(url)
    if no_cookie["success"]:
        return no_cookie["data"], ""

    has_bot = is_bot_detection(no_cookie.get("error"))

    if has_bot:
        for _label, bypass_args in EXTRACTOR_BYPASS_ATTEMPTS:
            result = run_ytdlp_once(url, bypass_args)
            if result["success"]:
                return result["data"], ""

    results = {}
    with ThreadPoolExecutor(max_workers=len(COOKIE_BROWSERS)) as ex:
        futures = {
            ex.submit(run_ytdlp_once, url, ["--cookies-from-browser", b]): b
            for b in COOKIE_BROWSERS
        }
        for future in as_completed(futures):
            browser = futures[future]
            try:
                r = future.result()
                results[browser] = r
                if r["success"]:
                    return r["data"], browser
            except Exception:
                pass

    best_error = (
        "Bot detected. Log into YouTube in a browser and try again."
        if has_bot else (no_cookie.get("error") or "yt-dlp failed to fetch video info")
    )
    raise Exception(best_error)


# ── Format extraction ──

def extract_formats(info: dict) -> list[dict]:
    all_formats = info.get("formats", [])
    has_separate = any(
        f.get("vcodec") != "none" and f.get("acodec") == "none"
        for f in all_formats
    )

    if has_separate:
        heights = sorted(set(
            f.get("height", 0) for f in all_formats
            if f.get("vcodec") != "none" and f.get("height")
        ), reverse=True)
        merged = [
            {"formatId": f"bestvideo[height<={h}]+bestaudio/best",
             "label": f"{h}p", "height": h, "ext": "mp4"}
            for h in heights
        ]
        merged.insert(0, {
            "formatId": "bestvideo+bestaudio/best",
            "label": "Best Quality (merged)", "height": 9999, "ext": "mp4",
        })
    else:
        seen_heights = set()
        merged = []
        for f in all_formats:
            h = f.get("height")
            if (f.get("vcodec") != "none" and f.get("acodec") != "none"
                    and h and f.get("protocol") != "m3u8_native"
                    and h not in seen_heights):
                seen_heights.add(h)
                merged.append({
                    "formatId": f["format_id"], "label": f"{h}p",
                    "height": h, "ext": f.get("ext", "mp4"),
                })
        merged.sort(key=lambda x: x["height"], reverse=True)
        merged.insert(0, {
            "formatId": "best", "label": "Best Quality",
            "height": 9999, "ext": "mp4",
        })

    merged.append({"formatId": "bestaudio/best", "label": "Audio Only", "height": 0, "ext": "mp3"})
    return merged
