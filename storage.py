"""Atomic JSON I/O, history, settings, and safe file operations."""

import json
import os
import re
import tempfile
from typing import Any


USER_DATA_DIR = None


def get_user_data_dir() -> str:
    global USER_DATA_DIR
    if USER_DATA_DIR:
        return USER_DATA_DIR
    import sys
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        USER_DATA_DIR = os.path.join(base, "YouTube Fetcher")
    else:
        USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".youtube-fetcher")
    return USER_DATA_DIR


def _history_path() -> str:
    return os.path.join(get_user_data_dir(), "history.json")


def _settings_path() -> str:
    return os.path.join(get_user_data_dir(), "settings.json")


def _cookie_config_path() -> str:
    return os.path.join(get_user_data_dir(), "cookie-config.json")


# ── Atomic JSON I/O (H4) ──

def load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default if default is not None else []


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ── Filename sanitization ──

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_unique_filename(directory: str, base_name: str) -> str:
    exts = ("mp4", "webm", "mkv", "mp3", "m4a", "ogg", "wav", "opus")
    try:
        existing = os.listdir(directory)
    except OSError:
        return base_name
    candidate = base_name
    counter = 1
    while counter < 1000:
        has_conflict = any(
            f.lower() == f"{candidate}.{ext}"
            for f in existing
            for ext in exts
        )
        if not has_conflict:
            return candidate
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


# ── Path validation (C3) ──

def is_path_within(path: str, parent: str) -> bool:
    try:
        real_path = os.path.realpath(path)
        real_parent = os.path.realpath(parent)
        return real_path.startswith(real_parent + os.sep) or real_path == real_parent
    except (OSError, ValueError):
        return False


def safe_delete_file(file_path: str, allowed_dirs: list[str]) -> bool:
    try:
        if not file_path or not os.path.exists(file_path):
            return True
        real = os.path.realpath(file_path)
        if not any(is_path_within(real, d) for d in allowed_dirs):
            return False
        if os.path.isfile(real):
            os.remove(real)
        return True
    except OSError:
        return False


# ── History ──

def history_load() -> list:
    return load_json(_history_path(), [])


def history_save(entry: dict) -> None:
    if "id" not in entry:
        return
    history = load_json(_history_path(), [])
    idx = next((i for i, h in enumerate(history) if h.get("id") == entry["id"]), -1)
    if idx >= 0:
        history[idx] = entry
    else:
        history.insert(0, entry)
    save_json(_history_path(), history)


def history_delete(entry_id: str) -> None:
    history = [h for h in load_json(_history_path(), []) if h.get("id") != entry_id]
    save_json(_history_path(), history)


def history_clear() -> None:
    save_json(_history_path(), [])


# ── Settings ──

def load_settings() -> dict:
    return load_json(_settings_path(), {"max_concurrent": 1, "save_path": ""})


def save_settings(settings: dict) -> None:
    save_json(_settings_path(), settings)


# ── Cookie config ──

def load_cookie_config() -> dict:
    return load_json(_cookie_config_path(), {})


def save_cookie_config(working_browser: str | None) -> None:
    save_json(_cookie_config_path(), {"workingCookieBrowser": working_browser or ""})
