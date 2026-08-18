"""YouTube Fetcher — pywebview entry point."""

import os
import sys
import webview

from backend import Backend

APP_TITLE = "YouTube Fetcher"
WINDOW_WIDTH = 860
WINDOW_HEIGHT = 650
MIN_WIDTH = 720
MIN_HEIGHT = 420


def get_html_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
        return os.path.join(base, "index.html")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def get_icon_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
        candidate = os.path.join(base, "media", "icon.ico")
    else:
        candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "icon.ico")
    if os.path.exists(candidate):
        return candidate
    return None


def main():
    backend = Backend()

    icon_path = get_icon_path()
    icon_arg = icon_path if icon_path else None

    window = webview.create_window(
        title=APP_TITLE,
        url=get_html_path(),
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        js_api=backend,
        text_select=False,
        zoomable=False,
    )

    backend.set_window(window)

    debug = "--debug" in sys.argv
    if debug:
        webview.start(debug=True, gui="edgechromium", icon=icon_arg)
    else:
        webview.start(gui="edgechromium", icon=icon_arg)


if __name__ == "__main__":
    main()
