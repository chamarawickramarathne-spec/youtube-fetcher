"""Core backend: yt-dlp execution, history, settings, file operations."""

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional


def get_user_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "YouTube Fetcher")
    return os.path.join(os.path.expanduser("~"), ".youtube-fetcher")


def get_history_path() -> str:
    return os.path.join(get_user_data_dir(), "history.json")


def get_settings_path() -> str:
    return os.path.join(get_user_data_dir(), "settings.json")


def get_cookie_config_path() -> str:
    return os.path.join(get_user_data_dir(), "cookie-config.json")


def load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_unique_filename(directory: str, base_name: str) -> str:
    exts = ["mp4", "webm", "mkv", "mp3", "m4a", "ogg", "wav", "opus"]
    try:
        existing = os.listdir(directory)
    except OSError:
        return base_name
    candidate = base_name
    counter = 1
    while True:
        has_conflict = any(
            f.lower() == f"{candidate}.{ext}"
            for f in existing
            for ext in exts
        )
        if not has_conflict:
            break
        counter += 1
        candidate = f"{base_name} ({counter})"
    return candidate


def shorten_path(p: str) -> str:
    if not p:
        return ""
    parts = p.replace("\\", "/").split("/")
    if len(parts) <= 3:
        return p
    return parts[0] + "/.../" + "/".join(parts[-2:])


COOKIE_BROWSERS = ["edge", "chrome", "brave", "vivaldi", "firefox"]
FETCH_TIMEOUT_MS = 30
DOWNLOAD_TIMEOUT_MS = 600
MAX_RETRIES = 2
RETRY_DELAY_MS = 3

EXTRACTOR_BYPASS_ATTEMPTS = [
    ("web+mweb client", ["--extractor-args", "youtube:player_client=web,mweb"]),
    ("android client", ["--extractor-args", "youtube:player_client=android"]),
    ("ios client", ["--extractor-args", "youtube:player_client=ios"]),
    ("tv client", ["--extractor-args", "youtube:player_client=tv"]),
]


class Backend:
    def __init__(self, window=None):
        self._window = window
        self._downloads: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._working_cookie_browser: Optional[str] = None
        self._update_state: dict = {
            "state": "idle", "version": "", "percent": 0, "message": ""
        }
        self._app_version = "2.0.0"
        os.makedirs(get_user_data_dir(), exist_ok=True)
        self._load_cookie_config()

    def set_window(self, window):
        self._window = window

    def _push_js(self, js_code: str) -> None:
        if self._window:
            try:
                self._window.evaluate_js(js_code)
            except Exception:
                pass

    def _push_event(self, event_name: str, data: dict) -> None:
        payload = json.dumps(data)
        self._push_js(f"window.{event_name}({payload})")

    def _load_cookie_config(self) -> None:
        config = load_json(get_cookie_config_path(), {})
        if "workingCookieBrowser" in config:
            self._working_cookie_browser = config["workingCookieBrowser"]

    def _save_cookie_config(self) -> None:
        save_json(get_cookie_config_path(), {
            "workingCookieBrowser": self._working_cookie_browser
        })

    # ── Path helpers ──

    def _get_ytdlp_path(self) -> str:
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
            candidate = os.path.join(base, "resources", "yt-dlp.exe")
            if os.path.exists(candidate):
                return candidate
        dev = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "yt-dlp.exe")
        if os.path.exists(dev):
            return dev
        return "yt-dlp"

    def _get_ffmpeg_dir(self) -> str:
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
            candidate = os.path.join(base, "resources")
            if os.path.exists(os.path.join(candidate, "ffmpeg.exe")):
                return candidate
        dev_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
        if os.path.exists(os.path.join(dev_dir, "ffmpeg.exe")):
            return dev_dir
        return ""

    def _get_downloads_dir(self, output_dir: str = "") -> str:
        if output_dir:
            return output_dir
        return os.path.join(os.path.expanduser("~"), "Downloads", "YouTube Fetcher")

    # ── yt-dlp single run ──

    def _run_ytdlp_once(self, url: str, extra_args: list[str] | None = None) -> dict:
        args = [
            self._get_ytdlp_path(),
            "--dump-single-json", "--no-download", "--no-warnings",
            "--no-check-certificates", "--no-playlist", "--js-runtimes", "node",
        ]
        if extra_args:
            args.extend(extra_args)
        args.append(url)

        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            stdout, stderr = proc.communicate(timeout=FETCH_TIMEOUT_MS)
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
            proc.kill()
            proc.wait()
            return {"success": False, "error": "Fetch timed out after 30 seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _is_bot_detection(error: str | None) -> bool:
        if not error:
            return False
        return "Sign in to confirm" in error or "bot" in error

    def _run_ytdlp_json(self, url: str) -> dict:
        if self._working_cookie_browser not in (None, ""):
            result = self._run_ytdlp_once(url, ["--cookies-from-browser", self._working_cookie_browser])
            if result["success"]:
                return result["data"]
            self._working_cookie_browser = None
            self._save_cookie_config()

        no_cookie = self._run_ytdlp_once(url)
        if no_cookie["success"]:
            self._working_cookie_browser = ""
            self._save_cookie_config()
            return no_cookie["data"]

        has_bot = self._is_bot_detection(no_cookie.get("error"))

        if has_bot:
            for label, args in EXTRACTOR_BYPASS_ATTEMPTS:
                result = self._run_ytdlp_once(url, args)
                if result["success"]:
                    self._working_cookie_browser = ""
                    self._save_cookie_config()
                    return result["data"]

        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=len(COOKIE_BROWSERS)) as ex:
            futures = {
                ex.submit(
                    self._run_ytdlp_once, url, ["--cookies-from-browser", b]
                ): b for b in COOKIE_BROWSERS
            }
            for future in as_completed(futures):
                browser = futures[future]
                try:
                    r = future.result()
                    results[browser] = r
                    if r["success"]:
                        self._working_cookie_browser = browser
                        self._save_cookie_config()
                        return r["data"]
                except Exception:
                    pass

        best_error = (
            "Bot detected. Log into YouTube in a browser (Edge/Chrome/Firefox) and try again, or the video may be restricted."
            if has_bot else (no_cookie.get("error") or "yt-dlp failed to fetch video info")
        )
        raise Exception(best_error)

    # ── API: Fetch info ──

    def fetch_info(self, url: str) -> dict:
        info = self._run_ytdlp_json(url)
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
                {"formatId": f"bestvideo[height<={h}]+bestaudio/best", "label": f"{h}p", "height": h, "ext": "mp4"}
                for h in heights
            ]
            merged.insert(0, {"formatId": "bestvideo+bestaudio/best", "label": "Best Quality (merged)", "height": 9999, "ext": "mp4"})
        else:
            seen_heights = set()
            merged = []
            for f in all_formats:
                h = f.get("height")
                if (f.get("vcodec") != "none" and f.get("acodec") != "none"
                        and h and f.get("protocol") != "m3u8_native" and h not in seen_heights):
                    seen_heights.add(h)
                    merged.append({"formatId": f["format_id"], "label": f"{h}p", "height": h, "ext": f.get("ext", "mp4")})
            merged.sort(key=lambda x: x["height"], reverse=True)
            merged.insert(0, {"formatId": "best", "label": "Best Quality", "height": 9999, "ext": "mp4"})

        merged.append({"formatId": "bestaudio/best", "label": "Audio Only", "height": 0, "ext": "mp3"})

        return {
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "formats": merged,
        }

    # ── API: Download ──

    def start_download(self, download_id: str, url: str, format_id: str,
                       title: str, output_dir: str) -> dict:
        thread = threading.Thread(
            target=self._execute_download,
            args=(download_id, url, format_id, title, output_dir, 0),
            daemon=True,
        )
        thread.start()
        return {"success": True}

    def _execute_download(self, download_id: str, url: str, format_id: str,
                          title: str, output_dir: str, attempt: int = 0) -> None:
        downloads_dir = self._get_downloads_dir(output_dir)
        os.makedirs(downloads_dir, exist_ok=True)

        ytdlp = self._get_ytdlp_path()
        ffmpeg_dir = self._get_ffmpeg_dir()
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
            quality_label = f"{h_match.group(1)}p" if h_match else ("best" if format_id == "best" else format_id)

        safe_name = get_unique_filename(downloads_dir, f"{sanitize_filename(title)} [{quality_label}]")
        out_path = os.path.join(downloads_dir, f"{safe_name}.%(ext)s")

        args.extend([
            "-o", out_path,
            "--newline", "--progress", "--no-warnings",
            "--no-check-certificates", "--no-overwrites", "--no-playlist",
            "--js-runtimes", "node",
            "--concurrent-fragments", "8",
            "--socket-timeout", "30",
            "--http-chunk-size", "10485760",
        ])

        if ffmpeg_dir:
            args.extend(["--ffmpeg-location", ffmpeg_dir])
        else:
            self._push_event("onLog", {"downloadId": download_id, "message": "Warning: ffmpeg not found, merge may fail"})

        if self._working_cookie_browser:
            args.extend(["--cookies-from-browser", self._working_cookie_browser])
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
            self._push_event("onError", {"downloadId": download_id, "message": f"Failed to start yt-dlp: {e}"})
            return

        tracked_file = ""
        start_time = time.time()

        try:
            for line in proc.stdout:
                text = line.decode("utf-8", errors="replace")
                m = re.search(r"(\d+\.?\d*)%", text)
                if m:
                    speed_m = re.search(r"at\s+([\d.]+\w+/s)", text)
                    eta_m = re.search(r"ETA\s+(\S+)", text)
                    self._push_event("onProgress", {
                        "downloadId": download_id,
                        "percent": float(m.group(1)),
                        "speed": speed_m.group(1) if speed_m else None,
                        "eta": eta_m.group(1) if eta_m else None,
                    })
                dest_m = re.search(r"\[download\]\s+Destination:\s+(.+)", text)
                if dest_m:
                    tracked_file = dest_m.group(1).strip()
                    self._push_event("onDestination", {"downloadId": download_id, "filePath": tracked_file})
                merge_m = re.search(r'\[Merger\]\s+Merging formats into\s+"(.+)"', text)
                if merge_m:
                    tracked_file = merge_m.group(1).strip()
                    self._push_event("onDestination", {"downloadId": download_id, "filePath": tracked_file})

                if time.time() - start_time > DOWNLOAD_TIMEOUT_MS:
                    proc.kill()
                    with self._lock:
                        self._downloads.pop(download_id, None)
                    self._push_event("onError", {"downloadId": download_id, "message": "Download timed out after 10 minutes"})
                    return

            stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
            for line in stderr_text.split("\n"):
                line = line.strip()
                if line and any(kw in line for kw in ["ERROR", "error", "Merge", "ffmpeg"]):
                    self._push_event("onLog", {"downloadId": download_id, "message": line})

            proc.wait()
            with self._lock:
                self._downloads.pop(download_id, None)

            if proc.returncode == 0:
                self._push_event("onComplete", {"downloadId": download_id, "filePath": tracked_file})
            else:
                if attempt < MAX_RETRIES:
                    self._push_event("onLog", {"downloadId": download_id, "message": f"Retrying... (attempt {attempt + 2}/{MAX_RETRIES + 1})"})
                    time.sleep(RETRY_DELAY_MS)
                    self._execute_download(download_id, url, format_id, title, output_dir, attempt + 1)
                else:
                    msg = f"yt-dlp exited with code {proc.returncode}"
                    self._push_event("onError", {"downloadId": download_id, "message": msg})
        except Exception as e:
            with self._lock:
                self._downloads.pop(download_id, None)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_MS)
                self._execute_download(download_id, url, format_id, title, output_dir, attempt + 1)
            else:
                self._push_event("onError", {"downloadId": download_id, "message": str(e)})

    def cancel_download(self, download_id: str) -> dict:
        with self._lock:
            proc = self._downloads.pop(download_id, None)
        if proc:
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass
            self._push_event("onError", {"downloadId": download_id, "message": "Cancelled"})
        return {"success": True}

    # ── History ──

    def history_load(self) -> list:
        return load_json(get_history_path(), [])

    def history_save(self, entry: dict) -> None:
        history = load_json(get_history_path(), [])
        idx = next((i for i, h in enumerate(history) if h["id"] == entry["id"]), -1)
        if idx >= 0:
            history[idx] = entry
        else:
            history.insert(0, entry)
        save_json(get_history_path(), history)

    def history_delete(self, entry_id: str) -> None:
        history = [h for h in load_json(get_history_path(), []) if h["id"] != entry_id]
        save_json(get_history_path(), history)

    def history_clear(self) -> None:
        save_json(get_history_path(), [])

    # ── File ops ──

    def delete_file(self, file_path: str) -> bool:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception:
            return False

    # ── Settings ──

    def get_settings(self) -> dict:
        return load_json(get_settings_path(), {"max_concurrent": 1, "save_path": ""})

    def save_settings(self, settings: dict) -> None:
        save_json(get_settings_path(), settings)

    # ── Folder picker ──

    def select_folder(self) -> str | None:
        if not self._window:
            return None
        try:
            result = self._window.create_file_dialog(
                0,  # FOLDER_DIALOG
                allow_multiple=False,
            )
            if result and len(result) > 0:
                return result[0]
        except Exception:
            pass
        return None

    # ── Clipboard ──

    def clipboard_paste(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""

    # ── Version ──

    def get_app_version(self) -> str:
        return self._app_version

    # ── Auto-update (GitHub) ──

    def check_for_updates(self) -> dict:
        if not getattr(sys, "frozen", False):
            self._update_state = {
                "state": "error", "version": "", "percent": 0,
                "message": "Updates are only available in the installed app"
            }
            return self._update_state

        thread = threading.Thread(target=self._check_update_thread, daemon=True)
        thread.start()
        self._update_state = {**self._update_state, "state": "checking", "message": "Checking for updates..."}
        self._push_event("onUpdateStatus", self._update_state)
        return self._update_state

    def _check_update_thread(self) -> None:
        import urllib.request
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/chamarawickramarathne-spec/youtube-fetcher/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "")
            version = tag.lstrip("v")
            if self._compare_versions(version, self._app_version) > 0:
                setup_asset = next(
                    (a for a in data.get("assets", []) if a["name"].endswith("-setup.exe")),
                    None,
                )
                if setup_asset:
                    self._update_state = {
                        "state": "available", "version": version, "percent": 0,
                        "message": f"Version {version} is available",
                        "download_url": setup_asset["browser_download_url"],
                    }
                else:
                    self._update_state = {
                        "state": "not-available", "version": "", "percent": 0,
                        "message": "You are up to date"
                    }
            else:
                self._update_state = {
                    "state": "not-available", "version": "", "percent": 0,
                    "message": "You are up to date"
                }
        except Exception as e:
            self._update_state = {
                "state": "error", "version": "", "percent": 0,
                "message": str(e) or "Update check failed"
            }
        self._push_event("onUpdateStatus", self._update_state)

    def download_update(self) -> bool:
        if self._update_state.get("state") != "available":
            return False
        thread = threading.Thread(target=self._download_update_thread, daemon=True)
        thread.start()
        return True

    def _download_update_thread(self) -> None:
        import urllib.request
        url = self._update_state.get("download_url", "")
        if not url:
            return
        self._update_state = {
            **self._update_state, "state": "downloading", "percent": 0,
            "message": "Downloading update..."
        }
        self._push_event("onUpdateStatus", self._update_state)
        try:
            tmp_dir = os.path.join(get_user_data_dir(), "update")
            os.makedirs(tmp_dir, exist_ok=True)
            installer_path = os.path.join(tmp_dir, "youtube-fetcher-setup.exe")

            def reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    pct = min(100, int(block_num * block_size * 100 / total_size))
                    self._update_state = {
                        **self._update_state, "percent": pct,
                        "message": f"Downloading update... {pct}%"
                    }
                    self._push_event("onUpdateStatus", self._update_state)

            urllib.request.urlretrieve(url, installer_path, reporthook)
            self._update_state = {
                **self._update_state, "state": "downloaded", "percent": 100,
                "message": f"Version {self._update_state.get('version', '')} downloaded",
                "installer_path": installer_path,
            }
            self._push_event("onUpdateStatus", self._update_state)
        except Exception as e:
            self._update_state = {
                **self._update_state, "state": "error",
                "message": f"Download failed: {e}"
            }
            self._push_event("onUpdateStatus", self._update_state)

    def install_update(self) -> bool:
        installer = self._update_state.get("installer_path", "")
        if not installer or not os.path.exists(installer):
            return False
        try:
            subprocess.Popen([installer], shell=False)
            import ctypes
            ctypes.windll.user32.PostQuitMessage(0)
            return True
        except Exception:
            return False

    def get_update_state(self) -> dict:
        return self._update_state

    @staticmethod
    def _compare_versions(a: str, b: str) -> int:
        def parse(v: str) -> list[int]:
            return [int(x) for x in re.findall(r"\d+", v)]
        pa, pb = parse(a), parse(b)
        for i in range(max(len(pa), len(pb))):
            va = pa[i] if i < len(pa) else 0
            vb = pb[i] if i < len(pb) else 0
            if va != vb:
                return 1 if va > vb else -1
        return 0
