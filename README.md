# ClipMaker

Turn a long video (a file, or a YouTube/TikTok/Instagram/Facebook link) into
ranked, ready-to-post vertical clips (15–180s) with burned-in captions —
running entirely on your own machine except for the one call to Claude that
scores which moments are worth clipping.

## What it does

1. **Get the video** — either a file you drop in, or a link (via `yt-dlp`)
2. **Transcribe locally** — `faster-whisper` runs on your machine, no upload
3. **Find the best moments** — the transcript is sent to Claude, which picks
   hooks, punchlines, and complete story beats between 15–180 seconds
4. **Cut & format** — `ffmpeg` extracts each clip, crops to 9:16, and burns
   in captions
5. **Review & download** — clips show up in the app, ranked by a 1–10
   virality score, ready to preview and download

## One-time setup (Windows)

1. **Install Python 3.10+** from [python.org](https://www.python.org/downloads/)
   — during install, check "Add Python to PATH".

2. **Install ffmpeg**:
   - Download a build from [gyan.dev's ffmpeg builds](https://www.gyan.dev/ffmpeg/builds/) (get the "essentials" zip)
   - Unzip it somewhere permanent, e.g. `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to your system PATH (Settings → System → About →
     Advanced system settings → Environment Variables → Path → New)
   - Confirm it worked: open a new Command Prompt and run `ffmpeg -version`

3. **Get an Anthropic API key** from [console.anthropic.com](https://console.anthropic.com)
   (Settings → API Keys). You'll paste this into the app each time — it's
   never saved to disk.

4. **Unzip this ClipMaker folder** anywhere, e.g. `C:\Tools\ClipMaker`.

## Running it

Double-click **`run.bat`**.

The first run will:
- create a local Python virtual environment (`venv` folder)
- install all dependencies
- open ClipMaker in its own window

Every run after that is fast — it reuses the same environment.

> The first time you process a video, `faster-whisper` will download its
> model (small = ~500MB) — that only happens once per model size you use.

## Using the app

1. Either drop in a video file, or switch to "Paste link" and paste a
   YouTube/TikTok/Instagram/Facebook video URL
2. Paste your Anthropic API key
3. Pick transcription accuracy (Balanced is a good default; use Fast for
   quick drafts, Most accurate for noisy audio or non-English content)
4. Click **Find the clips**
5. Watch the status update through: downloading → transcribing → finding
   moments → cutting clips
6. Preview and download each ranked clip

Clips are also saved to `outputs/<job-id>/` inside the ClipMaker folder if
you'd rather grab them from disk (e.g. to feed straight into your n8n
posting workflow).

## Notes & good-to-knows

- **Only clip content you have the rights to re-edit and repost.** Most
  platforms' terms don't allow downloading and reposting other creators'
  videos — this tool is built for your own footage or licensed content.
- Cropping is currently a **center crop** to 9:16. If your source video has
  important action off-center (e.g. two people talking, one on each side),
  you may want to manually re-crop specific clips afterward.
- Captions are burned in with a simple bold bottom-third style. If you want
  a different caption look (position, font, karaoke word-highlighting),
  that's a small change in `pipeline/clipper.py` — happy to adjust it.
- Longer source videos and higher accuracy models take longer to transcribe.
  A 30-minute video on "small" is usually a few minutes on a normal laptop.
- If `ffmpeg` isn't found, double check step 2 above — the app depends on it
  being on your system PATH.

## Project structure

```
clipmaker/
  app.py              Flask backend (routes + job orchestration)
  desktop.py          Opens the app as a native desktop window
  run.bat             One-click Windows launcher
  requirements.txt
  pipeline/
    downloader.py     File upload + URL download (yt-dlp)
    transcribe.py     Local transcription (faster-whisper)
    analyze.py         Claude-based clip scoring
    clipper.py         ffmpeg cutting, 9:16 crop, caption burn-in
  templates/index.html
  static/style.css, script.js
  uploads/            Downloaded/uploaded source videos
  outputs/<job_id>/   Generated clips per run
```
