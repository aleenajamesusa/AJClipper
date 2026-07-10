"""
downloader.py
Handles pulling video from a URL (YouTube, TikTok, Instagram, Facebook, etc.)
using yt-dlp, and normalizing local file uploads. Both paths return a local
mp4 path that the rest of the pipeline treats identically.
"""
import os
import uuid
import yt_dlp


def is_url(value: str) -> bool:
    return value.strip().lower().startswith(("http://", "https://"))


def download_from_url(url: str, output_dir: str, progress_hook=None) -> str:
    """
    Downloads a video from a supported platform link (YouTube, TikTok,
    Instagram, Facebook, X, etc.) and returns the local file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    job_name = uuid.uuid4().hex[:10]
    out_template = os.path.join(output_dir, f"{job_name}.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        # merge_output_format may change extension to mp4 after postprocessing
        root, _ = os.path.splitext(filepath)
        mp4_path = root + ".mp4"
        if os.path.exists(mp4_path):
            return mp4_path
        if os.path.exists(filepath):
            return filepath
    raise FileNotFoundError("Download completed but output file was not found.")


def save_uploaded_file(file_storage, output_dir: str) -> str:
    """Saves a Flask uploaded file (werkzeug FileStorage) to disk and returns its path."""
    os.makedirs(output_dir, exist_ok=True)
    job_name = uuid.uuid4().hex[:10]
    ext = os.path.splitext(file_storage.filename)[1] or ".mp4"
    dest = os.path.join(output_dir, f"{job_name}{ext}")
    file_storage.save(dest)
    return dest
