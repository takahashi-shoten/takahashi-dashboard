"""Diagnostics (needs GEMINI_API_KEY): (1) pricing/rate-limit text from Google's public pages, (2) ONE small TTS call, printing the full 429 error body if any
(quota metric / retry info). Never prints the key. Makes no video/image calls."""
import json
import re

import requests

from . import gemini


def page_lines(url, kws, width=450, maxhits=3):
    try:
        h = requests.get(url, timeout=60).text
    except Exception as e:
        print("PAGE FAIL", url, e); return
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", t)
    for kw in kws:
        for m in list(re.finditer(kw, t, flags=re.I))[:maxhits]:
            print("PAGE", url.rsplit("/", 1)[-1], kw, "::", t[max(0, m.start() - 150): m.start() + width])


def tts_once():
    body = {"contents": [{"parts": [{"text": "こんにちは。テストです。"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Iapetus"}}}}}
    r = requests.post(f"{gemini.BASE}gemini-3.8-flash-tts:generateContent", json=body, timeout=120,
                      headers={"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"})
    print("TTS status", r.status_code)
    print("TTS headers", {k: v for k, v in r.headers.items() if k.lower().startswith(("retry", "x-ratelimit"))})
    print("TTS body", r.text[:3000] if r.status_code != 200 else "ok (audio returned)")


def main():
    page_lines("https://ai.google.dev/gemini-api/docs/pricing", ["omni", "tts", "per second", "video"])
    page_lines("https://ai.google.dev/gemini-api/docs/rate-limits", ["tier 1", "text-to-speech", "tts", "per day", "RPD"])
    tts_once()


if __name__ == "__main__":
    main()
