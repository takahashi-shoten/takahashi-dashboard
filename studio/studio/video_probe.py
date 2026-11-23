"""Live probe: can the Gemini 'omni' models return a short video clip from a text prompt? (needs GEMINI_API_KEY). Files go to work/gemini_live/. Never prints the key."""
import base64
import time
from pathlib import Path

from . import gemini

PROMPT = ("Vertical 9:16 realistic phone-camera video, 8 seconds: two golden retrievers stand on their hind legs "
          "with front paws on a parked car, a police officer pats them down, funny and cute, night parking lot, natural handheld footage.")
MODELS = ["gemini-omni-flash-preview", "gemini-omni-1.1-flash", "gemini-omni-1.2-flash"]


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        for label, cfg in (("default", None), ("video+text", {"responseModalities": ["VIDEO", "TEXT"]})):
            body = {"contents": [{"parts": [{"text": PROMPT}]}]}
            if cfg:
                body["generationConfig"] = cfg
            t = time.time()
            try:
                r = gemini.generate_content(model, body, timeout=600)
            except Exception as e:  # report, keep probing the other models
                print(f"{model} [{label}]: FAIL {str(e)[:400]}")
                continue
            kinds = []
            for p in (r.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in p:
                    d = p["inlineData"]; mime = d.get("mime_type") or d.get("mimeType", "")
                    kinds.append(f"inline:{mime}:{len(d.get('data',''))}b64")
                    if mime.startswith("video"):
                        (out / f"{model}_{label}.mp4").write_bytes(base64.b64decode(d["data"]))
                elif "fileData" in p:
                    kinds.append(f"file:{p['fileData']}")
                elif "text" in p:
                    kinds.append("text:" + p["text"][:120])
            print(f"{model} [{label}]: ok in {round(time.time()-t,1)}s parts={kinds} usage={gemini.usage(r)}")


if __name__ == "__main__":
    main()
