"""
app.py
Flask backend for ClipMaker. Runs the full pipeline as a background thread
per job: (download or use uploaded video) -> transcribe -> analyze -> cut clips.
Serves a simple UI and a small JSON API the frontend polls for progress.
"""
import os
import threading
import traceback
import uuid

from flask import Flask, request, jsonify, render_template, send_from_directory

from pipeline import downloader, transcribe, analyze, clipper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

# In-memory job store. Fine for a single-user local desktop app.
JOBS = {}


def _set_status(job_id, status, **extra):
    JOBS[job_id].update({"status": status, **extra})


def run_pipeline(job_id: str, source: str, is_url: bool, api_key: str, model_size: str):
    try:
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        _set_status(job_id, "downloading" if is_url else "preparing")
        if is_url:
            def hook(d):
                if d.get("status") == "downloading":
                    pct = d.get("_percent_str", "").strip()
                    _set_status(job_id, "downloading", detail=pct)
            video_path = downloader.download_from_url(source, UPLOAD_DIR, progress_hook=hook)
        else:
            video_path = source  # already saved to disk by the upload route

        _set_status(job_id, "transcribing", detail="0%")

        def progress_cb(current, total):
            pct = f"{(current/total*100):.0f}%" if total else ""
            _set_status(job_id, "transcribing", detail=pct)

        segments, full_text, duration = transcribe.transcribe_video(
            video_path, model_size=model_size, progress_cb=progress_cb
        )

        _set_status(job_id, "analyzing")
        candidates = analyze.analyze_transcript(full_text, api_key, duration)

        if not candidates:
            _set_status(job_id, "error", detail="No strong clip candidates were found in this video.")
            return

        all_words = [w for seg in segments for w in seg["words"]]

        _set_status(job_id, "clipping", detail=f"0/{len(candidates)}")
        results = []
        for i, c in enumerate(candidates, start=1):
            start = float(c["start_seconds"])
            end = float(c["end_seconds"])
            out_name = f"clip_{i:02d}.mp4"
            out_path = os.path.join(job_dir, out_name)
            clipper.extract_clip(video_path, start, end, all_words, out_path)
            results.append({
                "file": out_name,
                "title": c.get("title", f"Clip {i}"),
                "hook_reason": c.get("hook_reason", ""),
                "virality_score": c.get("virality_score", None),
                "start": start,
                "end": end,
                "duration": round(end - start, 1),
            })
            _set_status(job_id, "clipping", detail=f"{i}/{len(candidates)}")

        _set_status(job_id, "done", results=results)
    except Exception as e:
        traceback.print_exc()
        _set_status(job_id, "error", detail=str(e))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/process", methods=["POST"])
def process():
    api_key = request.form.get("api_key", "").strip()
    model_size = request.form.get("model_size", "small").strip() or "small"
    url = request.form.get("video_url", "").strip()
    file = request.files.get("video_file")

    if not api_key:
        return jsonify({"error": "Anthropic API key is required."}), 400
    if not url and not file:
        return jsonify({"error": "Provide a video file or a video URL."}), 400

    job_id = uuid.uuid4().hex[:12]

    if url:
        source, is_url = url, True
    else:
        source, is_url = downloader.save_uploaded_file(file, UPLOAD_DIR), False

    JOBS[job_id] = {"status": "queued"}
    thread = threading.Thread(
        target=run_pipeline, args=(job_id, source, is_url, api_key, model_size), daemon=True
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)


@app.route("/clips/<job_id>/<filename>")
def serve_clip(job_id, filename):
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    return send_from_directory(job_dir, filename)


if __name__ == "__main__":
    app.run(port=5175, debug=False)
