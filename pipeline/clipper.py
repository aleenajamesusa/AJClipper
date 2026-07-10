"""
clipper.py
Cuts a segment from the source video, center-crops it to 9:16, and burns in
styled captions generated from the word-level transcript timestamps.
Requires ffmpeg to be installed and on PATH.
"""
import os
import subprocess
import tempfile


def _format_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(words: list, clip_start: float, clip_end: float, max_words_per_line: int = 5) -> str:
    """Builds an SRT string for words falling inside [clip_start, clip_end],
    re-based to clip-relative time, chunked into short readable lines."""
    in_range = [w for w in words if clip_start <= w["start"] < clip_end]
    lines = []
    chunk = []
    for w in in_range:
        chunk.append(w)
        if len(chunk) >= max_words_per_line:
            lines.append(chunk)
            chunk = []
    if chunk:
        lines.append(chunk)

    srt_parts = []
    for i, line_words in enumerate(lines, start=1):
        start = line_words[0]["start"] - clip_start
        end = line_words[-1]["end"] - clip_start
        text = " ".join(w["word"].strip() for w in line_words)
        srt_parts.append(f"{i}\n{_format_srt_time(max(start,0))} --> {_format_srt_time(max(end,0.1))}\n{text}\n")
    return "\n".join(srt_parts)


def extract_clip(source_path: str, start: float, end: float, words: list,
                  out_path: str, target_w: int = 1080, target_h: int = 1920):
    """
    Cuts [start, end] from source_path, crops/scales to target_w x target_h
    (default 1080x1920 = 9:16 2K-ready vertical), and burns in captions.
    """
    duration = end - start

    with tempfile.TemporaryDirectory() as tmpdir:
        srt_path = os.path.join(tmpdir, "captions.srt")
        srt_content = build_srt(words, start, end)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Center-crop to 9:16 then scale to target resolution, burn subtitles
        # styled as bold bottom-third captions.
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        vf = (
            f"crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
            f"scale={target_w}:{target_h},"
            f"subtitles='{srt_escaped}':force_style="
            "'FontName=Arial Black,FontSize=20,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,"
            "Alignment=2,MarginV=120'"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(duration),
            "-i", source_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")

    return out_path
