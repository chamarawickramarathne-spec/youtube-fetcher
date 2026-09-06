"""Download execution with rate limiting (M5), path validation (M2), and safe cancel (M4)."""

import os
import re
import subprocess
import threading
import time

from storage import (
    get_user_data_dir, safe_delete_file, sanitize_filename,
    get_unique_filename, is_path_within,
)
from ytdlp_runner import get_ytdlp_path, get_ffmpeg_dir


DOWNLOAD_TIMEOUT = 600
MAX_RETRIES = 2
RETRY_DELAY = 3
MAX_CONCURRENT = 10
DOWNLOADS_ROOT = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube Fetcher")


class DownloadManager:
    def __init__(self):
        self._downloads: dict[str, subprocess.Popen] = {}
        self._cancel_flags: dict[str, bool] = {}
        self._lock = threading.Lock()
        self._push_fn = None

    def set_push(self, push_fn) -> None:
        self._push_fn = push_fn

    def _emit(self, event: str, data: dict) -> None:
        if self._push_fn:
            try:
                self._push_fn(event, data)
            except Exception:
                pass

    def get_active_count(self) -> int:
        with self._lock:
            return len(self._downloads)

    def start(self, download_id: str, url: str, format_id: str,
              title: str, output_dir: str, cookie_browser: str | None) -> None:
        with self._lock:
            if len(self._downloads) >= MAX_CONCURRENT:
                self._emit("onError", {
                    "downloadId": download_id,
                    "message": "Too many concurrent downloads",
                })
                return
            self._cancel_flags[download_id] = False

        thread = threading.Thread(
            target=self._execute,
            args=(download_id, url, format_id, title, output_dir,
                  cookie_browser, 0),
            daemon=True,
        )
        thread.start()

    def cancel(self, download_id: str) -> None:
        with self._lock:
            self._cancel_flags[download_id] = True
            proc = self._downloads.pop(download_id, None)
        if proc:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
            self._emit("onError", {
                "downloadId": download_id, "message": "Cancelled",
            })

    def delete_file(self, file_path: str) -> bool:
        allowed = [DOWNLOADS_ROOT, get_user_data_dir()]
        return safe_delete_file(file_path, allowed)

    # ── Private ──

    def _get_downloads_dir(self, output_dir: str = "") -> str:
        if output_dir:
            real = os.path.realpath(output_dir)
            if not is_path_within(real, DOWNLOADS_ROOT):
                if not is_path_within(real, get_user_data_dir()):
                    if not is_path_within(real, os.path.expanduser("~")):
                        return DOWNLOADS_ROOT
            return output_dir
        return DOWNLOADS_ROOT

    def _execute(self, download_id: str, url: str, format_id: str,
                 title: str, output_dir: str, cookie_browser: str | None,
                 attempt: int = 0) -> None:
        downloads_dir = self._get_downloads_dir(output_dir)
        os.makedirs(downloads_dir, exist_ok=True)

        ytdlp = get_ytdlp_path()
        ffmpeg_dir = get_ffmpeg_dir()
        args = []

        if format_id == "bestaudio/best":
            args.extend(["-f", "bestaudio/best", "-x", "--audio-format", "mp3"])
        elif format_id == "best" or "+" in format_id:
            args.extend(["-f", format_id if "+" in format_id else "bestvideo+bestaudio/best"])
            args.extend(["--merge-output-format", "mp4"])
        else:
            h = format_id.replace("p", "")
            args.extend(["-f", f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"])
            args.extend(["--merge-output-format", "mp4"])

        if "bestaudio" in format_id and "+" not in format_id:
            quality_label = "audio"
        else:
            h_match = re.search(r"height<=(\d+)", format_id)
            quality_label = f"{h_match.group(1)}p" if h_match else (
                "best" if format_id == "best" else format_id
            )

        safe_name = get_unique_filename(
            downloads_dir, f"{sanitize_filename(title)} [{quality_label}]",
        )
        out_path = os.path.join(downloads_dir, f"{safe_name}.%(ext)s")

        args.extend([
            "-o", out_path,
            "--newline", "--progress", "--no-warnings",
            "--no-playlist", "--js-runtimes", "node",
            "--concurrent-fragments", "8",
            "--socket-timeout", "30",
            "--http-chunk-size", "10485760",
        ])

        if ffmpeg_dir:
            args.extend(["--ffmpeg-location", ffmpeg_dir])
        else:
            self._emit("onLog", {
                "downloadId": download_id,
                "message": "Warning: ffmpeg not found, merge may fail",
            })

        if cookie_browser:
            args.extend(["--cookies-from-browser", cookie_browser])
        else:
            args.extend(["--extractor-args", "youtube:player_client=web,mweb"])

        args.append(url)

        try:
            proc = subprocess.Popen(
                [ytdlp] + args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            with self._lock:
                self._downloads[download_id] = proc
        except Exception as e:
            self._emit("onError", {
                "downloadId": download_id,
                "message": f"Failed to start yt-dlp: {e}",
            })
            return

        tracked_file = ""
        start_time = time.time()

        try:
            for line in proc.stdout:
                with self._lock:
                    if self._cancel_flags.get(download_id):
                        break

                text = line.decode("utf-8", errors="replace")
                m = re.search(r"(\d+\.?\d*)%", text)
                if m:
                    speed_m = re.search(r"at\s+([\d.]+\w+/s)", text)
                    eta_m = re.search(r"ETA\s+(\S+)", text)
                    self._emit("onProgress", {
                        "downloadId": download_id,
                        "percent": float(m.group(1)),
                        "speed": speed_m.group(1) if speed_m else None,
                        "eta": eta_m.group(1) if eta_m else None,
                    })
                dest_m = re.search(r"\[download\]\s+Destination:\s+(.+)", text)
                if dest_m:
                    tracked_file = dest_m.group(1).strip()
                    self._emit("onDestination", {
                        "downloadId": download_id,
                        "filePath": tracked_file,
                    })
                merge_m = re.search(
                    r'\[Merger\]\s+Merging formats into\s+"(.+)"', text,
                )
                if merge_m:
                    tracked_file = merge_m.group(1).strip()
                    self._emit("onDestination", {
                        "downloadId": download_id,
                        "filePath": tracked_file,
                    })

                if time.time() - start_time > DOWNLOAD_TIMEOUT:
                    proc.kill()
                    with self._lock:
                        self._downloads.pop(download_id, None)
                    self._emit("onError", {
                        "downloadId": download_id,
                        "message": "Download timed out after 10 minutes",
                    })
                    return

            stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
            for line in stderr_text.split("\n"):
                line = line.strip()
                if line and any(kw in line for kw in ["ERROR", "error", "Merge", "ffmpeg"]):
                    self._emit("onLog", {"downloadId": download_id, "message": line})

            proc.wait()
            with self._lock:
                self._downloads.pop(download_id, None)
                was_cancelled = self._cancel_flags.pop(download_id, False)

            if was_cancelled:
                return

            if proc.returncode == 0:
                self._emit("onComplete", {
                    "downloadId": download_id, "filePath": tracked_file,
                })
            else:
                if attempt < MAX_RETRIES:
                    self._emit("onLog", {
                        "downloadId": download_id,
                        "message": f"Retrying... (attempt {attempt + 2}/{MAX_RETRIES + 1})",
                    })
                    time.sleep(RETRY_DELAY)
                    self._execute(
                        download_id, url, format_id, title,
                        output_dir, cookie_browser, attempt + 1,
                    )
                else:
                    self._emit("onError", {
                        "downloadId": download_id,
                        "message": f"yt-dlp exited with code {proc.returncode}",
                    })
        except Exception as e:
            with self._lock:
                self._downloads.pop(download_id, None)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                self._execute(
                    download_id, url, format_id, title,
                    output_dir, cookie_browser, attempt + 1,
                )
            else:
                self._emit("onError", {
                    "downloadId": download_id, "message": str(e),
                })
