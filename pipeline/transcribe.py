"""
transcribe.py
Runs local, offline transcription using faster-whisper. Produces both
sentence-level segments (for the LLM to analyze) and word-level timestamps
(for burning in captions later). Nothing here touches the network.
"""
from faster_whisper import WhisperModel

_MODEL_CACHE = {}


def get_model(model_size: str = "small", device: str = "auto", compute_type: str = "auto"):
    key = (model_size, device, compute_type)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _MODEL_CACHE[key]


def transcribe_video(video_path: str, model_size: str = "small", progress_cb=None):
    """
    Returns:
        segments: list of dicts {start, end, text, words: [{start,end,word}, ...]}
        full_text: full transcript as one string with [mm:ss] markers, for LLM analysis
    """
    model = get_model(model_size)
    seg_iter, info = model.transcribe(
        video_path,
        word_timestamps=True,
        vad_filter=True,  # skip silence, improves segment quality
    )

    segments = []
    text_lines = []
    for seg in seg_iter:
        words = [{"start": w.start, "end": w.end, "word": w.word} for w in (seg.words or [])]
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": words,
        })
        mm, ss = divmod(int(seg.start), 60)
        text_lines.append(f"[{mm:02d}:{ss:02d}] {seg.text.strip()}")
        if progress_cb:
            progress_cb(seg.end, info.duration)

    full_text = "\n".join(text_lines)
    return segments, full_text, info.duration
