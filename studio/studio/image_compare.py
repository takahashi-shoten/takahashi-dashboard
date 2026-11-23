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
H1 = ("Dramatic historical illustration, Japanese Sengoku era 1560: a rain-soaked mountain pass at dawn, an army of ashigaru foot soldiers in simple armour "
      "marching in a long line, banners wet and heavy, grey mist, painterly realistic style, cinematic composition.")
H2 = ("Dramatic historical illustration, Japanese Bakumatsu era 1867: a narrow night street in Kyoto lit by paper lanterns, two samurai in dark haori "
      "talking in low voices under the eaves, painterly realistic style, cinematic composition.")
JOBS = [("cmp_hist_flash_1.png", "gemini-3.1-flash-image", H1), ("cmp_hist_lite_1.png", "gemini-3.1-flash-lite-image", H1),
        ("cmp_hist_flash_2.png", "gemini-3.1-flash-image", H2), ("cmp_hist_lite_2.png", "gemini-3.1-flash-lite-image", H2)]


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, model, prompt in JOBS:
        g = visuals.GeminiImage(model=model, style="illustration")
        t = time.time()
        try:
            g.generate(prompt, out / name)
            print(f"OK {name} | model={model} | seconds={round(time.time() - t, 1)} | usage={g.last_usage}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name} | model={model} | {type(e).__name__}: {str(e)[:250]}"); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
