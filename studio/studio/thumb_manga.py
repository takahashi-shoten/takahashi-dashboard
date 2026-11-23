"""Manga-style two-panel thumbnail (the pattern seen in top Japanese story videos): setup panel + twist panel, speech bubbles with the story's own lines,
huge outlined headline. Panels are generated WITHOUT text; all Japanese text is drawn locally so it is never garbled. Needs GEMINI_API_KEY and Noto Sans CJK Bold.
Writes variants to work/gemini_live/thumb_*.png."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import visuals

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
SIZE = (1280, 720)
PANEL_L = ("A smug middle-aged Japanese office boss in a grey suit, arms crossed, sneering down at a tired young warehouse supervisor in a blue work jacket "
           "who stands with a worn notebook under his arm. Warehouse office background. Comic panel, close-up on the two faces.")
PANEL_R = ("The same boss now pale, frozen, eyes wide with shock and sweat drops, holding a document; the calm warehouse supervisor in the blue work jacket "
           "behind him quietly holding the notebook, faint smile. Comic panel, dramatic close-up, speed lines.")

# headline_top, headline_bottom, bubble_left, bubble_right
VARIANTS = {
    "a": ("手柄を横取りした課長", "契約書の3ページ目で青ざめた結果", "全部俺の手柄だ", "え…3ページ目…？"),
    "b": ("残業を消された現場主任", "ノート1冊で全員が固まった", "お前の残業？ないよ", "その記録は…まさか"),
    "c": ("怒鳴らず、言いふらさず", "正式な窓口に出しただけ", "騒ぐなよ、無能", "監査…？聞いてない"),
}


def font(px):
    return ImageFont.truetype(FONT_BOLD, px, index=0)


def outlined(draw, xy, text, px, fill, stroke=(0, 0, 0), sw=10):
    draw.text(xy, text, font=font(px), fill=fill, stroke_width=sw, stroke_fill=stroke)


def fit_px(draw, text, max_w, start=150, min_px=60, sw=10):
    px = start
    while px > min_px and draw.textlength(text, font=font(px)) + 2 * sw > max_w:
        px -= 4
    return px


def bubble(draw, box, text, tail):
    x0, y0, x1, y1 = box
    draw.ellipse(box, fill=(255, 255, 255), outline=(0, 0, 0), width=5)
    edge = y0 + 12 if tail[1] < y0 else y1 - 12                 # tail leaves the top edge when it points up, else the bottom edge
    draw.polygon([tail, (x0 + (x1 - x0) * 0.35, edge), (x0 + (x1 - x0) * 0.6, edge)], fill=(255, 255, 255), outline=(0, 0, 0))
    px = fit_px(draw, text, (x1 - x0) * 0.82, start=54, min_px=26, sw=0)
    w = draw.textlength(text, font=font(px))
    draw.text((x0 + (x1 - x0 - w) / 2, y0 + (y1 - y0 - px) / 2 - 4), text, font=font(px), fill=(0, 0, 0))


def compose(left_path, right_path, variant, out_path):
    top, bottom, bl, br = VARIANTS[variant]
    W, H = SIZE
    canvas = Image.new("RGB", SIZE, (15, 15, 20))
    for k, p in enumerate((left_path, right_path)):
        im = Image.open(p).convert("RGB")
        pw = W // 2 + 40
        im = im.resize((pw, int(im.height * pw / im.width)))
        im = im.crop((0, max(0, (im.height - (H - 250)) // 2), pw, max(0, (im.height - (H - 250)) // 2) + (H - 250))) if im.height > H - 250 else im
        canvas.paste(im, (0 if k == 0 else W // 2 - 40, 150))
    d = ImageDraw.Draw(canvas)
    d.polygon([(W // 2 - 70, 150), (W // 2 + 10, 150), (W // 2 - 30, H - 100), (W // 2 - 110, H - 100)], fill=(255, 215, 0))
    d.polygon([(W // 2 - 20, 410), (W // 2 + 50, 450), (W // 2 - 20, 490)], fill=(230, 0, 40), outline=(255, 255, 255))
    d.rectangle((0, 0, W, 150), fill=(215, 20, 30))
    px = fit_px(d, top, W - 60, start=118)
    outlined(d, ((W - d.textlength(top, font=font(px))) / 2, 12), top, px, (255, 255, 255), sw=9)
    d.rectangle((0, H - 120, W, H), fill=(0, 0, 0))
    px = fit_px(d, bottom, W - 60, start=96, sw=8)
    outlined(d, ((W - d.textlength(bottom, font=font(px))) / 2, H - 112), bottom, px, (255, 225, 0), sw=8)
    bubble(d, (24, 462, 400, 578), bl, (170, 400))      # below the boss's face, tail pointing up to him
    bubble(d, (W - 420, 164, W - 40, 262), br, (W - 560, 340))
    canvas.save(out_path)
    return out_path


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    g = visuals.GeminiImage(style="manga")
    g.generate(PANEL_L, out / "panel_l.png", size=(1280, 1024))
    g.generate(PANEL_R, out / "panel_r.png", size=(1280, 1024))
    for v in VARIANTS:
        compose(out / "panel_l.png", out / "panel_r.png", v, out / f"thumb_{v}.png")
    print("thumbnail variants written:", sorted(p.name for p in out.glob("thumb_*.png")), "image usage:", g.usage)


if __name__ == "__main__":
    main()
