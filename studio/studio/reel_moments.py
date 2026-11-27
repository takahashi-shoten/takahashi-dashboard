"""Pick reel-worthy moments from ONE long recording (e.g. a 40-minute kimono dressing) with Gemini video+audio understanding.

Dry-run tool for the beauty-SNS project (docs/projects/beauty_sns/). It only ANALYSES (no download, no cutting): it asks for moments with timestamps,
reports the cost/time the API reports, and flags privacy risks (faces, customer speech). Cutting is done later by footage_short.py on the shop's own footage.
Usage: python -m studio.reel_moments <youtube_url_or_id> [model]"""
import json
import re
import sys
from pathlib import Path

from . import video_analysis

PROMPT = """You are helping a small kimono-dressing (kitsuke) salon turn ONE long recording into several short Instagram Reels.
Watch the ACTUAL video (frames and audio). Return JSON: {"video": {"summary": str, "duration_seen": "MM:SS", "camera": str},
 "moments": [{"start": "MM:SS", "end": "MM:SS", "length_s": int (8-30), "type": one of [hands_closeup, finished_look, before_after, process_timelapse, tip_explanation, atmosphere],
 "why_reel_worthy": str, "what_is_seen": str (only directly observed), "caption_ja": str (draft Instagram caption, no income/result guarantees),
 "text_overlay_ja": str (max 11 chars per line), "face_or_customer_visible": bool, "customer_speech_audible": bool, "confidence": number 0-1}],
 "timelapse_candidate": {"start": "MM:SS", "end": "MM:SS", "why": str},
 "not_observable": [str]}
Rules: return 6-10 moments spread over the whole video, non-overlapping; only timestamps you actually observed; never invent; list what you cannot judge in not_observable."""


def mmss(s):
    """'MM:SS' or 'H:MM:SS' -> seconds; None if malformed."""
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,3}):(\d{2})", (s or "").strip())
    if not m:
        return None
    h, mi, se = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    return h * 3600 + mi * 60 + se


def clean_moments(data):
    """Keep only moments with valid, ordered timestamps and 3-60 s length; drop overlaps. Returns (kept, dropped_count)."""
    kept, dropped = [], 0
    for m in sorted((data or {}).get("moments", []), key=lambda x: mmss(x.get("start")) or 0):
        a, b = mmss(m.get("start")), mmss(m.get("end"))
        if a is None or b is None or not (3 <= b - a <= 60) or (kept and a < mmss(kept[-1]["end"])):
            dropped += 1
            continue
        kept.append(m)
    return kept, dropped


def main():
    video, model = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "gemini-3.5-flash-lite")
    res = video_analysis.analyze(video, model, prompt=PROMPT, max_out=8000)
    kept, dropped = clean_moments(res["json"])
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    vid = re.sub(r"[^A-Za-z0-9_-]", "", video.split("v=")[-1])[:20]
    (out / f"reelmoments_{vid}_{model}.json").write_text(json.dumps(dict(res, kept=kept, dropped=dropped), ensure_ascii=False, indent=1), encoding="utf-8")
    v, a = video_analysis.video_input_confirmed(res["usage"])
    print("REELMOMENTS model", model, "| seconds", res["seconds"], "| usage", res["usage"], "| est_cost_usd", res["cost_usd"], "| video_tokens", v, "| audio_tokens", a,
          "| moments_valid", len(kept), "| dropped", dropped, "| duration_seen", ((res["json"] or {}).get("video") or {}).get("duration_seen"))
    for m in kept:
        print(" ", m.get("start"), m.get("end"), m.get("type"), "| face", m.get("face_or_customer_visible"), "| speech", m.get("customer_speech_audible"), "|", (m.get("why_reel_worthy") or "")[:80])


if __name__ == "__main__":
    main()
