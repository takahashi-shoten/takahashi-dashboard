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


def price_sections():
    h = requests.get("https://ai.google.dev/gemini-api/docs/pricing", timeout=60).text
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", t)
    for head in ("## Gemini Omni 1.2 Flash", "## Gemini Omni 1.1 Flash", "## Gemini 3.8 Flash TTS"):
        i = t.find(head)
        print("SECTION", head, "::", t[i + 300: i + 2600] if i >= 0 else "not found")


def tts_burst(n=10, gap=6):
    import time
    body = {"contents": [{"parts": [{"text": "はい。テストです。"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Iapetus"}}}}}
    for i in range(n):
        r = requests.post(f"{gemini.BASE}gemini-3.8-flash-tts:generateContent", json=body, timeout=120,
                          headers={"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"})
        print("BURST", i, r.status_code, (r.text[:600] if r.status_code != 200 else ""))
        time.sleep(gap)


def main():
    price_sections()
    tts_burst()


if __name__ == "__main__":
    main()
