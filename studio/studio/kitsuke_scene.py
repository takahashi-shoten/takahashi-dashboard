"""Demo scenes for the salon short-video idea (needs GEMINI_API_KEY): kimono/hakama dressing, faces never visible.
AI-generated mock visuals only - NOT real customers or real work; label as images/illustration if ever shown publicly."""
import sys
import time
from pathlib import Path

from . import visuals

STYLE = ("Modern minimalist editorial photograph, vertical 9:16, gray-toned colour palette (concrete gray walls, charcoal and light-gray surfaces, "
         "muted desaturated colours with at most one subtle accent), soft diffused light, clean contemporary Japanese salon interior, "
         "shallow depth of field, calm and refined mood, no text, no logos, no watermark. No person's face is visible.")
JOBS = [
    ("kitsuke_1_obi_hands.png", f"{STYLE} Close-up of a kimono dresser's two hands tying the back bow of a hakama obi on a young woman in a graduation hakama (charcoal-gray hakama, light-gray kimono with a subtle pattern), shot from behind at waist height."),
    ("kitsuke_2_back_view.png", f"{STYLE} A young woman in a graduation hakama seen from behind in a bright room, the dresser's hands adjusting the large ribbon at her back, dark hair pinned up neatly."),
    ("kitsuke_3_accessories.png", f"{STYLE} Flat-lay on a wooden table: folded kimono, date-jime cords, obi-ita, himo ties, tabi socks and hair ornaments neatly arranged on a gray stone or concrete table, all in gray, white and charcoal tones with one muted accent colour, top-down view."),
    ("kitsuke_4_finished_back.png", f"{STYLE} Finished look: a woman in a hakama standing in a doorway of a bright room, photographed from behind, the hakama ribbon neat and symmetrical, soft gray light."),
]

FURISODE = [
    ("kitsuke_f1_obi_hands.png", f"{STYLE} Close-up from behind: a kimono dresser's two hands shaping the large decorative obi bow on a young woman in a furisode (long-sleeved formal kimono) in muted gray-lavender with a subtle pattern; long sleeves hang beside her; charcoal and ivory obi."),
    ("kitsuke_f2_back_view.png", f"{STYLE} A young woman in an elegant furisode seen from behind in a bright gray concrete room, long sleeves, a large obi bow, hair up with a small ornament; the dresser's hands lightly adjusting the obi at her back."),
    ("kitsuke_f4_finished_back.png", f"{STYLE} Finished look: a woman in a furisode with long sleeves standing in a doorway of a calm modern room, photographed from behind, neat obi bow, soft gray light, face never visible."),
]

# Structure taken from public dressing guides (kimonomachi hakama guide; kasya furisode obi guide), see docs/research/obi_structure_2026-11-26.md
HAKAMA_FACTS = ("Accurate women's graduation hakama over a nishaku-sode (short-sleeved furisode-style) kimono in muted light gray with a thin gray date-eri collar layer; "
                "the hakama is charcoal with 3 crisp pleats on the back; a flat stiff back board (koshi-ita) sits on top of the obi; "
                "above it a hanhaba-obi RIBBON in bunko style: two flat wings angled slightly upward, its tail folded into two soft peaks resting over the knot, "
                "top edge against the back and bottom edge slightly away from the body; "
                "the hakama's own back ties form a small butterfly bow slightly off-centre on the back board with two tails of UNEQUAL length.")
FURISODE_FACTS = ("Accurate furisode with a stiff brocade fukuro obi tied in a symmetrical two-tier bunko style: two large upper wings and two lower wings forming a ribbon, "
                  "a silk obi-age scarf softly visible along the top edge of the knot and an obi-jime cord across the centre of the knot; the long sleeves hang straight down.")
REAL = [
    ("kitsuke_r_h1a.png", f"{STYLE} {HAKAMA_FACTS} Close-up from behind: only the dresser's hands (her face not in frame) spreading the ribbon wings."),
    ("kitsuke_r_h1b.png", f"{STYLE} {HAKAMA_FACTS} Close-up from behind: only the dresser's hands (her face not in frame) spreading the ribbon wings."),
    ("kitsuke_r_h2a.png", f"{STYLE} {HAKAMA_FACTS} Full back view of the woman standing in a calm gray room, nobody else in frame."),
    ("kitsuke_r_h2b.png", f"{STYLE} {HAKAMA_FACTS} Full back view of the woman standing in a calm gray room, nobody else in frame."),
    ("kitsuke_r_f1a.png", f"{STYLE} {FURISODE_FACTS} Close-up from behind: only the dresser's hands (her face not in frame) adjusting the wings; muted gray-lavender furisode, charcoal-and-silver obi."),
    ("kitsuke_r_f1b.png", f"{STYLE} {FURISODE_FACTS} Close-up from behind: only the dresser's hands (her face not in frame) adjusting the wings; muted gray-lavender furisode, charcoal-and-silver obi."),
    ("kitsuke_r_f2a.png", f"{STYLE} {FURISODE_FACTS} Full back view of the young woman standing in a calm gray room, nobody else in frame; hair up with a small ornament."),
    ("kitsuke_r_f2b.png", f"{STYLE} {FURISODE_FACTS} Full back view of the young woman standing in a calm gray room, nobody else in frame; hair up with a small ornament."),
]

# Owner-liked obi shape (Commons "Kimono backshot by sth", checked by eye from the owner's screenshot): bold, voluminous, LAYERED wings flowing diagonally from the left shoulder to the right, asymmetric.
ACCENT_FACTS = ("Accurate furisode in charcoal and gray tones with a subtle pattern and long sleeves; the ONLY accent colour is the obi: a bold, voluminous brocade obi in vermilion, deep red and gold "
                "tied in a modern layered style with several overlapping wings that sweep diagonally upward from the left shoulder to the right (asymmetric, like a tateya-style knot with layers), "
                "a soft silk obi-age scarf along the top edge of the knot; a small hair ornament in red and ivory.")
ACCENT = [
    ("kitsuke_b_f1a.png", f"{STYLE} {ACCENT_FACTS} Close-up from behind at shoulder-to-waist height: only the dresser's hands (face not in frame) lifting and shaping one of the layered wings."),
    ("kitsuke_b_f1b.png", f"{STYLE} {ACCENT_FACTS} Close-up from behind at shoulder-to-waist height: only the dresser's hands (face not in frame) lifting and shaping one of the layered wings."),
    ("kitsuke_b_f2a.png", f"{STYLE} {ACCENT_FACTS} Full back view of the young woman standing in a calm modern gray room, nobody else in frame."),
    ("kitsuke_b_f2b.png", f"{STYLE} {ACCENT_FACTS} Full back view of the young woman standing in a calm modern gray room, nobody else in frame."),
]


def main(which="hakama"):
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, prompt in (ACCENT if which == "accent" else REAL if which == "real" else FURISODE if which == "furisode" else JOBS):
        g = visuals.GeminiImage(model="gemini-3.1-flash-image", style="photo")
        t = time.time()
        try:
            g.generate(prompt, out / name, size=(1080, 1920))
            print(f"OK {name} | seconds={round(time.time() - t, 1)} | usage={g.last_usage}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name} | {type(e).__name__}: {str(e)[:250]}"); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "hakama"))
