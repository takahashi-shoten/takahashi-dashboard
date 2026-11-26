"""Demo scenes for the salon short-video idea (needs GEMINI_API_KEY): kimono/hakama dressing, faces never visible.
AI-generated mock visuals only - NOT real customers or real work; label as images/illustration if ever shown publicly."""
import sys
import time
from pathlib import Path

from . import visuals

STYLE = ("Photorealistic editorial photograph, vertical 9:16, soft natural window light, bright clean Japanese home salon interior, "
         "shallow depth of field, no text, no logos, no watermark. No person's face is visible.")
JOBS = [
    ("kitsuke_1_obi_hands.png", f"{STYLE} Close-up of a kimono dresser's two hands tying the back bow of a hakama obi on a young woman in a graduation hakama (burgundy hakama, patterned furisode sleeve), shot from behind at waist height."),
    ("kitsuke_2_back_view.png", f"{STYLE} A young woman in a graduation hakama seen from behind in a bright room, the dresser's hands adjusting the large ribbon at her back, long dark hair pinned up."),
    ("kitsuke_3_accessories.png", f"{STYLE} Flat-lay on a wooden table: folded kimono, date-jime cords, obi-ita, himo ties, tabi socks and hair ornaments neatly arranged, soft morning light, top-down view."),
    ("kitsuke_4_finished_back.png", f"{STYLE} Finished look: a woman in a hakama standing in a doorway of a bright room, photographed from behind, the hakama ribbon neat and symmetrical, warm light."),
]


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, prompt in JOBS:
        g = visuals.GeminiImage(model="gemini-3.1-flash-image", style="photo")
        t = time.time()
        try:
            g.generate(prompt, out / name, size=(1080, 1920))
            print(f"OK {name} | seconds={round(time.time() - t, 1)} | usage={g.last_usage}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name} | {type(e).__name__}: {str(e)[:250]}"); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
