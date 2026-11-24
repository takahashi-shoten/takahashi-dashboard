"""Real video understanding with Gemini (video + audio), for learning from marketing examples (docs/MANAGEMENT_PRINCIPLES.md, directive of 2026-11-24).

analyze_youtube(): passes a public YouTube URL (official 'YouTube URL' preview feature) or an uploaded file to a Gemini model together with a structured prompt.
Findings must separate OBSERVED FACTS from INTERPRETATION and carry a timestamp. This module never claims it analysed the video unless the API reports
video/audio input tokens (see `input_tokens_by_modality`). Cost is computed from reported usage and the price table parsed from Google's pricing page."""
import json
import re
import sys
import time
from pathlib import Path

import requests

from . import gemini

PROMPT_ITEMS = """Analyse the ACTUAL video (frames AND audio), not just its title. Return JSON: {"video": {"summary": str, "language": str, "duration_seen": "MM:SS"},
 "findings": [{"category": one of [hook, structure, speech_and_delivery, voice_pace_pauses, face_gaze_gesture, camera_background_lighting, on_screen_text_editing_cuts,
 bgm_sfx_volume, retention_devices, emotional_words, authority_trust_empathy, desire_anxiety_appeal, copywriting, call_to_action, sales_funnel],
 "time": "MM:SS", "observed_fact": str (only what is directly seen/heard, quote short phrases), "interpretation": str (your reading; may be empty), "evidence": str,
 "source": one of [visual, audio, on_screen_text, transcript, inferred], "confidence": number 0-1}],
 "not_observable": [str]}  Rules: give at least 25 findings spread over the whole video with timestamps; never invent what you cannot see/hear (list it in not_observable);
 keep quotes under 15 words; no more than one quote per finding."""

_PRICE_CACHE = {}


def price_per_m(model):
    """(input_video_usd_per_M, output_usd_per_M) parsed from the pricing page; None if not found."""
    if model in _PRICE_CACHE:
        return _PRICE_CACHE[model]
    h = requests.get("https://ai.google.dev/gemini-api/docs/pricing", timeout=60).text
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)))
    i = t.find(f'id="{model}"')
    out = (None, None)
    if i >= 0:
        seg = re.sub(r"\{%.*?%\}", " ", t[i: i + 1800])
        a = re.search(r"Input price[^$]*\$([0-9.]+)", seg)
        b = re.search(r"Output price[^$]*\$([0-9.]+)", seg)
        out = (float(a.group(1)) if a else None, float(b.group(1)) if b else None)
    _PRICE_CACHE[model] = out
    return out


def usage_summary(resp):
    u = resp.get("usageMetadata", {})
    by = {d.get("modality"): d.get("tokenCount") for d in u.get("promptTokensDetails", [])}
    return dict(prompt=u.get("promptTokenCount"), output=u.get("candidatesTokenCount"), thoughts=u.get("thoughtsTokenCount"), total=u.get("totalTokenCount"), by_modality=by)


def estimate_cost(model, u):
    pin, pout = price_per_m(model)
    if pin is None or pout is None:
        return None
    return round((u["prompt"] or 0) * pin / 1e6 + ((u["output"] or 0) + (u["thoughts"] or 0)) * pout / 1e6, 4)


def analyze(video, model, prompt=PROMPT_ITEMS, resolution="low", start=None, end=None, is_file_uri=False, max_out=16000):
    """video: YouTube URL/ID or a Gemini Files API uri. Returns dict(text, json, usage, seconds, cost_usd)."""
    uri = video if is_file_uri or video.startswith("http") else f"https://www.youtube.com/watch?v={video}"
    part = {"fileData": {"fileUri": uri, "mimeType": "video/mp4"}} if is_file_uri else {"fileData": {"fileUri": uri}}
    if start or end:
        part["videoMetadata"] = {k: v for k, v in (("startOffset", start), ("endOffset", end)) if v}
    body = {"contents": [{"parts": [part, {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_out,
                                 "mediaResolution": "MEDIA_RESOLUTION_LOW" if resolution == "low" else "MEDIA_RESOLUTION_MEDIUM"}}
    t = time.time()
    resp = gemini.generate_content(model, body, timeout=900)
    sec = round(time.time() - t, 1)
    text = gemini.text_of(resp)
    u = usage_summary(resp)
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    return dict(text=text, json=data, usage=u, seconds=sec, cost_usd=estimate_cost(model, u), model=model, uri=uri)


def video_input_confirmed(u):
    """True only if the API counted VIDEO (and AUDIO) input tokens: otherwise we cannot say the video was analysed."""
    m = u.get("by_modality", {})
    return bool(m.get("VIDEO")), bool(m.get("AUDIO"))


def main():
    video, model = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "gemini-3.5-flash-lite")
    res = analyze(video, model)
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    vid = re.sub(r"[^A-Za-z0-9_-]", "", video.split("v=")[-1])[:20]
    (out / f"analysis_{vid}_{model}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    v, a = video_input_confirmed(res["usage"])
    print("ANALYSIS model", model, "| seconds", res["seconds"], "| usage", res["usage"], "| est_cost_usd", res["cost_usd"], "| video_tokens_counted", v, "| audio_tokens_counted", a,
          "| findings", len((res["json"] or {}).get("findings", [])))


if __name__ == "__main__":
    main()
