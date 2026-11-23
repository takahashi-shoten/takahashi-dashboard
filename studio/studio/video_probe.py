"""Live probe: can the Gemini 'omni' models return a short video clip via the Interactions API? (needs GEMINI_API_KEY).
Also prints the REST-relevant parts of Google's public doc page. Files go to work/gemini_live/. Never prints the key."""
import base64
import json
import re
import time
from pathlib import Path

import requests

from . import gemini

PROMPT = ("Vertical 9:16 realistic phone-camera video, 8 seconds: two golden retrievers stand on their hind legs "
          "with front paws on a parked car, a police officer pats them down, funny and cute, night parking lot, natural handheld footage.")
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def doc_excerpt():
    try:
        h = requests.get("https://ai.google.dev/gemini-api/docs/omni?hl=en", timeout=60).text
        t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
        t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", t)
        for kw in ("curl", "response_format", "steps", "aspect_ratio", "price", "Pricing", "duration", "background"):
            for m in list(re.finditer(kw, t))[:2]:
                print("DOC", kw, "::", t[max(0, m.start() - 200): m.start() + 500])
    except Exception as e:
        print("DOC fetch failed", e)


def find_video(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and len(v) > 5000 and k in ("data", "bytes", "video"):
                return path + "/" + k, v
            r = find_video(v, path + "/" + k)
            if r: return r
    elif isinstance(o, list):
        for i, v in enumerate(o):
            r = find_video(v, f"{path}[{i}]")
            if r: return r
    return None


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    doc_excerpt()
    hdr = {"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"}
    variants = {
        "plain": {"input": PROMPT},
        "rf_video": {"input": PROMPT, "response_format": {"type": "video", "aspect_ratio": "9:16"}},
    }
    for model in ["gemini-omni-1.1-flash", "gemini-omni-flash-preview"]:
        for label, extra in variants.items():
            t = time.time()
            r = requests.post(URL, json={"model": model, **extra}, headers=hdr, timeout=900)
            print(f"{model} [{label}] HTTP {r.status_code} in {round(time.time()-t,1)}s")
            try:
                j = r.json()
            except ValueError:
                print("non-json", r.text[:300]); continue
            hit = find_video(j)
            if hit:
                (out / f"{model}_{label}.mp4").write_bytes(base64.b64decode(hit[1]))
                print("VIDEO at", hit[0], "bytes", len(hit[1]))
                slim = json.loads(json.dumps(j)); 
                print("keys:", list(j.keys()), "usage:", j.get("usage") or j.get("usageMetadata"))
                break
            print(json.dumps(j)[:700])
        else:
            continue
        break


if __name__ == "__main__":
    main()
