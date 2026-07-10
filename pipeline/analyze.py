"""
analyze.py
Sends the timestamped transcript to Claude and asks it to identify the most
'clippable' segments: strong hooks, punchlines, emotional peaks, useful
standalone tips, or complete story beats. Each candidate must be between
15 and 180 seconds and align to natural sentence boundaries.
"""
import json
import re
from anthropic import Anthropic

SYSTEM_PROMPT = """You are an expert short-form video editor who has produced \
hundreds of viral TikTok/Reels/Shorts clips. You are given a timestamped \
transcript of a longer video. Your job is to find the segments most likely \
to perform well as standalone short clips.

Rules:
- Each clip must be between 15 and 180 seconds long.
- Clip boundaries must land on natural sentence/thought boundaries from the \
transcript timestamps given - never cut mid-sentence.
- Prioritize: strong hooks in the first 2 seconds, punchlines, surprising \
claims, emotional peaks, concrete useful tips, controversial or debate-worthy \
statements, and complete mini-stories with a beginning/middle/end.
- Do not invent content that is not in the transcript.
- Return ONLY valid JSON, no preamble, no markdown fences, matching exactly \
this schema:

{
  "clips": [
    {
      "start_seconds": 12.5,
      "end_seconds": 47.0,
      "title": "short punchy working title",
      "hook_reason": "one sentence on why this will grab attention in the first 2 seconds",
      "virality_score": 8
    }
  ]
}

virality_score is an integer 1-10. Return the clips array sorted by \
virality_score descending. Return at most 10 clips, only include clips you \
are genuinely confident about - quality over quantity."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def analyze_transcript(full_text: str, api_key: str, video_duration: float) -> list:
    client = Anthropic(api_key=api_key)
    user_prompt = (
        f"Video duration: {video_duration:.0f} seconds.\n\n"
        f"Timestamped transcript:\n{full_text}\n\n"
        "Identify the best short-clip candidates per the rules above."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = "".join(block.text for block in response.content if getattr(block, "text", None))
    data = _extract_json(raw)
    clips = data.get("clips", [])

    # Safety net: enforce duration bounds even if the model drifts
    valid_clips = []
    for c in clips:
        dur = c.get("end_seconds", 0) - c.get("start_seconds", 0)
        if 15 <= dur <= 180:
            valid_clips.append(c)
    valid_clips.sort(key=lambda c: c.get("virality_score", 0), reverse=True)
    return valid_clips
