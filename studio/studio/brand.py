"""Channel brand assets (icon + banner) for the owner to review and upload by hand. Needs GEMINI_API_KEY and an installed Japanese font.
Images are generated WITHOUT text; the Japanese text is drawn locally with Pillow so it is never garbled. Output: work/gemini_live/."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import visuals

FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
NAME = "静かなる逆転劇"
TAGLINE = "理不尽に、静かに、きっちり、やり返す。"
ICON_PROMPT = ("Minimal flat emblem for a channel about quiet workplace comeback stories: a single white chess king standing upright beside a "
               "toppled dark chess king, deep navy circular background, warm amber accent light, centered with generous padding, clean vector style.")
BANNER_PROMPT = ("Cinematic wide shot of an empty modern office at night seen from a long corridor, deep navy and teal tones, a single warm amber "
                 "desk lamp glowing on the far right, calm and tense mood, large dark empty space across the center and left for overlaid text.")


def compose_banner(bg_path, out_path, size=(2560, 1440)):
    img = Image.open(bg_path).convert("RGB").resize(size, Image.LANCZOS)
    shade = Image.new("RGBA", size, (5, 12, 28, 120))
    img = Image.alpha_composite(img.convert("RGBA"), shade)
    d = ImageDraw.Draw(img)
    big, small = ImageFont.truetype(FONT, 150), ImageFont.truetype(FONT, 52)
    cx, cy = size[0] // 2, size[1] // 2                      # keep text inside the centre safe area (about 1235 x 338 px)
    w1 = d.textlength(NAME, font=big)
    w2 = d.textlength(TAGLINE, font=small)
    d.text((cx - w1 / 2, cy - 120), NAME, font=big, fill=(255, 255, 255, 255))
    d.text((cx - w2 / 2, cy + 70), TAGLINE, font=small, fill=(255, 196, 94, 255))
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    g = visuals.GeminiImage(model="gemini-3.1-flash-image", style="illustration")
    g.generate(ICON_PROMPT, out / "icon_raw.png", size=(1024, 1024))
    Image.open(out / "icon_raw.png").convert("RGB").resize((800, 800), Image.LANCZOS).save(out / "channel_icon.png")
    g.generate(BANNER_PROMPT, out / "banner_bg.png", size=(2560, 1440))
    compose_banner(out / "banner_bg.png", out / "channel_banner.png")
    print("brand assets written:", sorted(p.name for p in out.glob("channel_*.png")), "image usage:", g.usage)


if __name__ == "__main__":
    main()
