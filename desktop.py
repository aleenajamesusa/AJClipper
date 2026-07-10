"""
desktop.py
Launches the Flask backend in a background thread and opens it in a native
desktop window (via pywebview) instead of a browser tab, so it feels like a
real installed app.
"""
import threading
import webview
from app import app


def start_flask():
    app.run(port=5175, debug=False, use_reloader=False)


if __name__ == "__main__":
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    webview.create_window("ClipMaker", "http://127.0.0.1:5175", width=720, height=900, resizable=True)
    webview.start()
