"""pywebview API bridge — composes storage, ytdlp_runner, updater, downloader."""

import json
import os
import sys
import webview

from storage import (
    get_user_data_dir, history_load, history_save, history_delete,
    history_clear, load_settings, save_settings, load_cookie_config,
    save_cookie_config, shorten_path,
)
from ytdlp_runner import is_valid_youtube_url, fetch_json, extract_formats
from updater import UpdateManager
from downloader import DownloadManager


class Backend:
    def __init__(self, window=None):
        self._window = window
        self._working_cookie_browser: str | None = self._load_cookie_browser()

        self._update = UpdateManager(get_user_data_dir())
        self._update.set_push(self._push_event)

        self._dl = DownloadManager()
        self._dl.set_push(self._push_event)

    def set_window(self, window):
        self._window = window

    # ── JS push (C5: ensure_ascii for injection safety) ──

    def _push_js(self, js_code: str) -> None:
        if self._window:
            try:
                self._window.evaluate_js(js_code)
            except Exception:
                pass

    def _push_event(self, event_name: str, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=True)
        self._push_js(f"window.{event_name}({payload})")

    # ── Cookie config ──

    def _load_cookie_browser(self) -> str | None:
        config = load_cookie_config()
        val = config.get("workingCookieBrowser")
        if val in (None, ""):
            return val
        return val if val else None

    def _save_cookie_browser(self, browser: str | None) -> None:
        self._working_cookie_browser = browser
        save_cookie_config(browser)

    # ── Public API ──

    def fetch_info(self, url: str) -> dict:
        if not is_valid_youtube_url(url):
            raise Exception("Invalid URL — only YouTube URLs are supported")

        data, cookie_browser = fetch_json(url, self._working_cookie_browser)
        if cookie_browser is not None and cookie_browser != self._working_cookie_browser:
            self._save_cookie_browser(cookie_browser)

        formats = extract_formats(data)
        return {
            "title": data.get("title", "Unknown"),
            "thumbnail": data.get("thumbnail", ""),
            "duration": data.get("duration", 0),
            "formats": formats,
        }

    def start_download(self, download_id: str, url: str, format_id: str,
                       title: str, output_dir: str) -> dict:
        self._dl.start(download_id, url, format_id, title,
                       output_dir, self._working_cookie_browser)
        return {"success": True}

    def cancel_download(self, download_id: str) -> dict:
        self._dl.cancel(download_id)
        return {"success": True}

    def history_load(self) -> list:
        return history_load()

    def history_save(self, entry: dict) -> None:
        history_save(entry)

    def history_delete(self, entry_id: str) -> None:
        history_delete(entry_id)

    def history_clear(self) -> None:
        history_clear()

    def delete_file(self, file_path: str) -> bool:
        return self._dl.delete_file(file_path)

    def get_settings(self) -> dict:
        return load_settings()

    def save_settings(self, settings: dict) -> None:
        allowed = {"max_concurrent": int, "save_path": str}
        cleaned = {}
        for k, t in allowed.items():
            if k in settings:
                try:
                    cleaned[k] = t(settings[k])
                except (ValueError, TypeError):
                    pass
        save_settings(cleaned)

    def select_folder(self) -> str | None:
        if not self._window:
            return None
        try:
            result = self._window.create_file_dialog(20, allow_multiple=False)
            if result and len(result) > 0:
                return result[0]
        except Exception:
            pass
        return None

    def clipboard_paste(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""

    def get_app_version(self) -> str:
        return "2.1.0"

    # ── Update API ──

    def check_for_updates(self) -> dict:
        return self._update.check(
            self.get_app_version(),
            getattr(sys, "frozen", False),
        )

    def download_update(self) -> bool:
        return self._update.download()

    def install_update(self) -> bool:
        return self._update.install()

    def get_update_state(self) -> dict:
        return self._update.get_state()
