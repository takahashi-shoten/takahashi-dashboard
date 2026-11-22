"""Photorealism comparison (needs GEMINI_API_KEY): same scene on two models + a second scene for a consistency check. Prints token usage."""
import sys
import time
from pathlib import Path

from . import visuals

CAST = ("a Japanese man in his early 50s with short graying hair and a navy knit sweater, and a Japanese woman in her mid 40s with shoulder-length "
        "dark brown hair and a cream cardigan")
SCENE1 = (f"Candid editorial photograph, 35mm lens, shallow depth of field, soft warm window light. {CAST}, sitting across a small wooden table "
          "in a quiet Tokyo cafe, he leans in listening attentively while she speaks with a gentle smile, two cups of coffee on the table.")
SCENE2 = (f"Candid editorial photograph, 35mm lens, natural overcast daylight. The same two people: {CAST}, walking side by side along a tree-lined "
          "path in a Tokyo park in autumn, talking and laughing softly.")
JOBS = [("cmp_flash_scene1.png", "gemini-3.1-flash-image", SCENE1), ("cmp_pro_scene1.png", "gemini-3-pro-image", SCENE1),
        ("cmp_flash_scene2.png", "gemini-3.1-flash-image", SCENE2)]


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, model, prompt in JOBS:
        g = visuals.GeminiImage(model=model, style="photo")
        t = time.time()
        try:
            g.generate(prompt, out / name)
            print(f"OK {name} | model={model} | seconds={round(time.time() - t, 1)} | usage={g.last_usage}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name} | model={model} | {type(e).__name__}: {str(e)[:250]}"); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
