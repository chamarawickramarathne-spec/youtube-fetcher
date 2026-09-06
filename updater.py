"""Auto-update system with SHA-256 checksum verification (C1)."""

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import urllib.request


GITHUB_REPO = "chamarawickramarathne-spec/youtube-fetcher"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXPECTED_CHECKSUMS = {}  # version -> sha256 hex (populated per release)


class UpdateManager:
    """Thread-safe update manager (H3: all state protected by lock)."""

    def __init__(self, user_data_dir: str):
        self._lock = threading.Lock()
        self._state: dict = {
            "state": "idle", "version": "", "percent": 0,
            "message": "", "download_url": "", "installer_path": "",
            "expected_sha256": "",
        }
        self._user_data_dir = user_data_dir
        self._push_fn = None

    def set_push(self, push_fn) -> None:
        self._push_fn = push_fn

    def get_state(self) -> dict:
        with self._lock:
            return {**self._state}

    def check(self, app_version: str, is_frozen: bool) -> dict:
        if not is_frozen:
            with self._lock:
                self._state = {
                    "state": "error", "version": "", "percent": 0,
                    "message": "Updates are only available in the installed app",
                    "download_url": "", "installer_path": "", "expected_sha256": "",
                }
            return self._state

        thread = threading.Thread(
            target=self._check_thread, args=(app_version,), daemon=True,
        )
        thread.start()
        with self._lock:
            self._state = {
                **self._state, "state": "checking",
                "message": "Checking for updates...",
            }
        self._emit()
        return self._get()

    def download(self) -> bool:
        with self._lock:
            if self._state.get("state") != "available":
                return False
        thread = threading.Thread(target=self._download_thread, daemon=True)
        thread.start()
        return True

    def install(self) -> bool:
        with self._lock:
            installer = self._state.get("installer_path", "")
        if not installer or not os.path.exists(installer):
            return False
        try:
            subprocess.Popen([installer], shell=False)
            import ctypes
            ctypes.windll.user32.PostQuitMessage(0)
            return True
        except Exception:
            return False

    # ── Private ──

    def _get(self) -> dict:
        with self._lock:
            return {**self._state}

    def _emit(self) -> None:
        if self._push_fn:
            try:
                self._push_fn("onUpdateStatus", self._get())
            except Exception:
                pass

    def _check_thread(self, app_version: str) -> None:
        try:
            req = urllib.request.Request(
                GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "")
            version = tag.lstrip("v")

            if _compare_versions(version, app_version) > 0:
                arch_suffix = _detect_arch()
                setup_asset = next(
                    (a for a in data.get("assets", [])
                     if a["name"].endswith(f"-setup-{arch_suffix}.exe")),
                    None,
                )
                if setup_asset:
                    checksum = _extract_checksum(data, arch_suffix)
                    with self._lock:
                        self._state = {
                            **self._state,
                            "state": "available",
                            "version": version,
                            "percent": 0,
                            "message": f"Version {version} is available",
                            "download_url": setup_asset["browser_download_url"],
                            "expected_sha256": checksum,
                        }
                else:
                    with self._lock:
                        self._state = {
                            **self._state,
                            "state": "not-available", "version": "",
                            "percent": 0, "message": "You are up to date",
                            "download_url": "", "expected_sha256": "",
                        }
            else:
                with self._lock:
                    self._state = {
                        **self._state,
                        "state": "not-available", "version": "",
                        "percent": 0, "message": "You are up to date",
                        "download_url": "", "expected_sha256": "",
                    }
        except Exception as e:
            with self._lock:
                self._state = {
                    **self._state,
                    "state": "error", "version": "", "percent": 0,
                    "message": str(e) or "Update check failed",
                    "download_url": "", "expected_sha256": "",
                }
        self._emit()

    def _download_thread(self) -> None:
        with self._lock:
            url = self._state.get("download_url", "")
            expected_sha = self._state.get("expected_sha256", "")
            version = self._state.get("version", "")

        if not url:
            return

        with self._lock:
            self._state = {
                **self._state, "state": "downloading", "percent": 0,
                "message": "Downloading update...",
            }
        self._emit()

        try:
            tmp_dir = os.path.join(self._user_data_dir, "update")
            os.makedirs(tmp_dir, exist_ok=True)
            installer_path = os.path.join(tmp_dir, "youtube-fetcher-setup.exe")

            def reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    pct = min(100, int(block_num * block_size * 100 / total_size))
                    with self._lock:
                        self._state = {
                            **self._state, "percent": pct,
                            "message": f"Downloading update... {pct}%",
                        }
                    self._emit()

            urllib.request.urlretrieve(url, installer_path, reporthook)

            if not expected_sha:
                os.remove(installer_path)
                with self._lock:
                    self._state = {
                        **self._state, "state": "error",
                        "message": "No SHA-256 checksum listed for this release — update aborted",
                        "download_url": "", "expected_sha256": "",
                    }
                self._emit()
                return

            actual = _sha256_file(installer_path)
            if actual.lower() != expected_sha.lower():
                os.remove(installer_path)
                with self._lock:
                    self._state = {
                        **self._state, "state": "error",
                        "message": "Checksum verification failed — download may be corrupted",
                        "download_url": "", "expected_sha256": "",
                    }
                self._emit()
                return

            with self._lock:
                self._state = {
                    **self._state, "state": "downloaded", "percent": 100,
                    "message": f"Version {version} downloaded",
                    "installer_path": installer_path,
                }
            self._emit()
        except Exception as e:
            with self._lock:
                self._state = {
                    **self._state, "state": "error",
                    "message": f"Download failed: {e}",
                }
            self._emit()


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


def _detect_arch() -> str:
    import struct
    bits = struct.calcsize("P") * 8
    return "x64" if bits == 64 else "x86"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_checksum(release_data: dict, arch_suffix: str) -> str:
    body = release_data.get("body", "")
    m = re.search(rf"sha256[- ]?{re.escape(arch_suffix)}[: ]+([a-fA-F0-9]{{64}})", body)
    if m:
        return m.group(1)
    return ""
