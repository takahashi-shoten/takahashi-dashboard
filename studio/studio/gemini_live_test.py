"""Live check of the Gemini integrations (needs GEMINI_API_KEY): one image + one Google-Search-grounded review.

The sample script contains one TRUE claim (Tokyo Tower height) and one FALSE claim (Mt. Fuji height) to see if the reviewer catches it.
Prints token usage (prices: check the Google pricing page; nothing is hardcoded). Never prints the key.
"""
import json
import sys
import time
from pathlib import Path

from . import qa, visuals
from .errors import NotConnected

SCRIPT = {
    "title_options": ["test"], "original_angle": "x", "hook": "h", "description": "d", "tags": [], "fact_claims_to_verify": [],
    "ai_disclosure_needed": True,
    "sections": [{"heading": "豆知識", "visual_prompt": "x", "seconds": 20,
                  "narration": "東京タワーの高さは333メートルです。また、富士山の標高は4,776メートルで、日本で一番高い山です。"}],
}
IMAGE_PROMPT = "A calm middle-aged man listening attentively to a woman across a cafe table, warm soft light, flat illustration style, wide shot"


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    img = visuals.GeminiImage()
    t = time.time()
    try:
        img.generate(IMAGE_PROMPT, out / "sample.png")
        from PIL import Image
        im = Image.open(out / "sample.png")
        print("image_model:", img.model, "| size:", im.size, "| seconds:", round(time.time() - t, 1), "| usage:", img.last_usage)
    except NotConnected as e:
        print("FAIL image: not connected:", e); rc = 1
    except Exception as e:  # noqa: BLE001
        print("FAIL image:", type(e).__name__, str(e)[:300]); rc = 1
    rev = qa.GeminiReviewer()
    t = time.time()
    try:
        r = rev.review(SCRIPT, "ja")
        print("review_model:", rev.model, "| seconds:", round(time.time() - t, 1), "| usage:", r["usage"])
        print("verdict:", r["verdict"])
        for i in r["issues"]:
            print("  issue:", i[:240])
        for c in r["unverified_claims"]:
            print("  unverified:", c[:240])
        caught = any(("4,776" in s) or ("4776" in s) or ("3,776" in s) or ("3776" in s) for s in r["issues"] + r["unverified_claims"])
        print("caught_false_claim_fuji:", caught, "| verdict_is_not_pass:", r["verdict"] != "pass")
    except NotConnected as e:
        print("FAIL review: not connected:", e); rc = 1
    except Exception as e:  # noqa: BLE001
        print("FAIL review:", type(e).__name__, str(e)[:300]); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
