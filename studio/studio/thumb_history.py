"""History thumbnail: one dramatic painted scene with the figures kept to the right, huge outlined text on the dark left, a red 'verified from sources' badge.
The image has NO text (the model garbles Japanese); all text is drawn locally. Needs GEMINI_API_KEY and Noto Sans CJK Bold. Writes work/gemini_live/hthumb_*.png."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import visuals

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
SIZE = (1280, 720)
PROMPT = ("Dramatic painterly historical illustration, Japan 1582, dawn: a temple compound engulfed in roaring flames and thick black smoke seen from the courtyard, "
          "silhouettes of armed soldiers with banners surrounding it, and on the burning veranda at the RIGHT side of the frame a lone lord in a robe and a young attendant "
          "kneeling beside him, both seen as dark silhouettes against the fire. Compose so the LEFT 45% of the frame is dark smoky sky with little detail (space for text). "
          "Cinematic lighting, deep red and orange fire against near-black, no text, no letters, no modern objects.")
# badge, big line 1 (yellow), big line 2 (white), caption (small, bottom)
VARIANTS = {
    "a": ("史料で検証", "本能寺", "最期の朝", "信長のそばにいた若者は、何を思ったのか"),
    "b": ("史料で検証", "信長の最期", "若者の一言", "「明智が者と見え申し候」"),
}


def font(px):
    return ImageFont.truetype(FONT_BOLD, px, index=0)


def fit(draw, text, max_w, start, min_px=60, sw=10):
    px = start
    while px > min_px and draw.textlength(text, font=font(px)) + 2 * sw > max_w:
        px -= 4
    return px


def compose(base_path, variant, out_path):
    badge, l1, l2, cap = VARIANTS[variant]
    W, H = SIZE
    im = Image.open(base_path).convert("RGB").resize(SIZE, Image.LANCZOS)
    shade = Image.new("L", SIZE, 0)                                   # left-to-right dark gradient so the text always reads
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line((x, 0, x, H), fill=int(170 * max(0.0, 1 - x / (W * 0.62))))
    im = Image.composite(Image.new("RGB", SIZE, (0, 0, 0)), im, shade.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    left_w = int(W * 0.56)
    bx, by = 36, 30
    bpx = 46
    bw = d.textlength(badge, font=font(bpx)) + 40
    d.rectangle((bx, by, bx + bw, by + bpx + 22), fill=(215, 20, 30))
    d.text((bx + 20, by + 8), badge, font=font(bpx), fill=(255, 255, 255))
    p1 = fit(d, l1, left_w, 190)
    d.text((36, 120), l1, font=font(p1), fill=(255, 225, 0), stroke_width=10, stroke_fill=(0, 0, 0))
    p2 = fit(d, l2, left_w, 170)
    d.text((36, 120 + p1 + 6), l2, font=font(p2), fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
    cp = fit(d, cap, W - 70, 48, min_px=30, sw=6)
    d.rectangle((0, H - cp - 36, W, H), fill=(0, 0, 0))
    d.text((36, H - cp - 22), cap, font=font(cp), fill=(255, 255, 255), stroke_width=0)
    im.save(out_path)
    return out_path


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    g = visuals.GeminiImage(model="gemini-3.1-flash-image", style="history")
    g.generate(PROMPT, out / "hist_base.png", size=SIZE)
    for v in VARIANTS:
        compose(out / "hist_base.png", v, out / f"hthumb_{v}.png")
    print("history thumbnails written:", sorted(p.name for p in out.glob("hthumb_*.png")), "image usage:", g.usage)


if __name__ == "__main__":
    main()
