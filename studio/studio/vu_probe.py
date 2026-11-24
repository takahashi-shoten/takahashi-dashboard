"""Stage-1 probe for video understanding (needs GEMINI_API_KEY, YOUTUBE_API_KEY). Prints, never the keys:
 (1) excerpts of Google's video-understanding doc and pricing page, (2) models that can take video (names only), (3) public metadata of the target video."""
import os
import re
import sys

import requests

from . import gemini

TARGET = sys.argv[1] if len(sys.argv) > 1 else "DYUxKuX0Bxc"


def page_text(url):
    h = requests.get(url, timeout=60).text
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def excerpts(url, kws, width=700, maxhits=2):
    try:
        t = page_text(url)
    except Exception as e:
        print("DOC FAIL", url, e); return
    for kw in kws:
        for m in list(re.finditer(kw, t, flags=re.I))[:maxhits]:
            print("DOC", url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1][:30], "|", kw, "::", t[max(0, m.start() - 120): m.start() + width])


def main():
    excerpts("https://ai.google.dev/gemini-api/docs/video-understanding", ["YouTube", "tokens per second", "fps", "media_resolution|mediaResolution", "maximum|limit", "timestamp", "file_uri|fileUri"])
    # models
    names = []
    tok = None
    while True:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 200, **({"pageToken": tok} if tok else {})},
                         headers={"x-goog-api-key": gemini.api_key()}, timeout=60).json()
        names += [(m["name"].split("/")[-1], m.get("supportedGenerationMethods", [])) for m in r.get("models", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    print("MODELS (generateContent, flash/pro/omni):", [n for n, mth in names if "generateContent" in mth and re.search(r"flash|pro|omni", n) and not re.search(r"image|tts|live|audio|embedding", n)])
    # pricing excerpts for flash / pro text models
    t = page_text("https://ai.google.dev/gemini-api/docs/pricing")
    for m in re.finditer(r"## (Gemini [0-9.]+ (?:Flash|Pro)(?:-Lite)?[^#{]{0,30}?) \{%", t):
        seg = t[m.end(): m.end() + 900]
        print("PRICE", m.group(1)[:40], "::", re.sub(r"\{%.*?%\}", " ", seg)[:420])
    # target metadata
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if key:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "snippet,contentDetails,statistics", "id": TARGET, "key": key}, timeout=30).json()
        for it in r.get("items", []):
            ch = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet,statistics", "id": it["snippet"]["channelId"], "key": key}, timeout=30).json()["items"][0]
            print("TARGET", dict(title=it["snippet"]["title"], channel=ch["snippet"]["title"], subs=ch["statistics"].get("subscriberCount"),
                               published=it["snippet"]["publishedAt"], duration=it["contentDetails"]["duration"], views=it["statistics"].get("viewCount"),
                               likes=it["statistics"].get("likeCount"), comments=it["statistics"].get("commentCount"), lang=it["snippet"].get("defaultAudioLanguage")))
        if not r.get("items"):
            print("TARGET not found via Data API:", r.get("error", {}).get("message", "")[:200])


if __name__ == "__main__":
    main()
