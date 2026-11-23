"""Manga-style two-panel thumbnail (the pattern seen in top Japanese story videos): setup panel + twist panel, speech bubbles with the story's own lines,
huge outlined headline. Panels are generated WITHOUT text; all Japanese text is drawn locally so it is never garbled. Needs GEMINI_API_KEY and Noto Sans CJK Bold.
Writes variants to work/gemini_live/thumb_*.png."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import visuals

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
SIZE = (1280, 720)
TALL_L = ("A tired but calm young Japanese man in a navy work jacket holding a worn notebook, standing in front of a smug middle-aged manager in a grey suit "
          "who sneers and points at him; warehouse office background. Vertical portrait panel, both faces clearly visible, upper bodies. "
          "Composition: the young man on the LEFT side of the frame, the manager on the RIGHT side of the frame.")
TALL_R = ("A middle-aged manager in a grey suit, pale and trembling with wide shocked eyes and sweat drops, gripping a document; behind him a young man in a navy work "
          "jacket calmly smiling, holding a notebook. Vertical portrait panel, dramatic, both faces clearly visible, upper bodies. "
          "Composition: the shocked manager large in the foreground on the LEFT side of the frame, the young man standing behind him on the RIGHT side of the frame.")
PANEL_L = ("A smug middle-aged Japanese office boss in a grey suit, arms crossed, sneering down at a tired young warehouse supervisor in a blue work jacket "
           "who stands with a worn notebook under his arm. Warehouse office background. Comic panel, close-up on the two faces.")
PANEL_R = ("The same boss now pale, frozen, eyes wide with shock and sweat drops, holding a document; the calm warehouse supervisor in the blue work jacket "
           "behind him quietly holding the notebook, faint smile. Comic panel, dramatic close-up, speed lines.")

# hook (red column), lower line 1, lower line 2 (black columns), bubble_left (the manager), bubble_right (the manager)
VARIANTS = {
    "a": ("手柄を横取りした課長", "契約書の３ページ目で", "青ざめた結果", "全部俺の手柄だ", "え…3ページ目…？"),
    "b": ("残業を消された現場主任", "ノート１冊で", "全員が固まった", "お前の残業？ないよ", "その記録は…まさか"),
    "c": ("怒鳴らず、言いふらさず", "正式な窓口に", "出しただけ", "騒ぐなよ、無能", "監査…？聞いてない"),
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
    top, l1, l2, bl, br = VARIANTS[variant]
    bottom = l1 + l2
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
    bubble(d, (W - 420, 164, W - 40, 262), br, (W - 400, 292))
    canvas.save(out_path)
    return out_path


def vtext(draw, x, y, text, px, fill, max_h=640, img=None):
    """Vertical Japanese text, one column, top to bottom (x = left edge of the column). Shrinks to fit max_h.
    Long-vowel marks are drawn rotated 90 degrees; commas/full stops sit at the upper right of their cell."""
    while px > 30 and len(text) * px * 1.02 > max_h:
        px -= 2
    f = font(px)
    for i, ch in enumerate(text):
        cx, cy = x, y + i * px * 1.02
        if ch in "ー―":                       # draw the vertical long-vowel bar ourselves (font glyphs come out horizontal)
            bx = cx + px * 0.5
            draw.rectangle((bx - px * 0.05, cy + px * 0.1, bx + px * 0.05, cy + px * 0.9), fill=fill)
            continue
        if ch in "、。":
            cx, cy = x + px * 0.55, cy - px * 0.45
        draw.text((cx, cy), ch, font=f, fill=fill)
    return px


def compose_v(left_path, right_path, variant, out_path):
    """Three columns like the top Japanese story-manga thumbnails: left panel | vertical headline strip | right panel, dialogue bubbles inside the panels."""
    top, line1, line2, bl, br = VARIANTS[variant]
    W, H = SIZE
    strip = 300
    pw = (W - strip) // 2
    canvas = Image.new("RGB", SIZE, (255, 255, 255))
    for k, p in enumerate((left_path, right_path)):
        im = Image.open(p).convert("RGB")
        im = im.resize((pw, int(im.height * pw / im.width)))
        top_off = max(0, (im.height - H) // 3)
        canvas.paste(im.crop((0, top_off, pw, top_off + H)), (0 if k == 0 else pw + strip, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle((pw, 0, pw + strip, H), fill=(255, 255, 255))
    d.line((pw, 0, pw, H), fill=(0, 0, 0), width=6)
    d.line((pw + strip, 0, pw + strip, H), fill=(0, 0, 0), width=6)
    vtext(d, pw + strip - 112, 22, top, 100, (225, 15, 40), max_h=H - 40, img=canvas)     # right column (read first): the hook
    vtext(d, pw + strip - 207, 22, line1, 84, (0, 0, 0), max_h=H - 40, img=canvas)       # lower line in two black columns, split at a phrase boundary
    vtext(d, pw + strip - 297, 22, line2, 84, (0, 0, 0), max_h=H - 40, img=canvas)
    bubble(d, (16, 22, pw - 16, 132), bl, (pw * 0.8, 175))     # tail points at the manager (right side of the left panel)
    bubble(d, (pw + strip + 16, 22, W - 16, 132), br, (pw + strip + 130, 200))     # tail points at the manager (left side of the right panel)
    canvas.save(out_path)
    return out_path


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    g = visuals.GeminiImage(style="manga")
    g.generate(TALL_L, out / "tall_l.png", size=(720, 1280))
    g.generate(TALL_R, out / "tall_r.png", size=(720, 1280))
    for v in VARIANTS:
        compose_v(out / "tall_l.png", out / "tall_r.png", v, out / f"thumb_{v}.png")
    print("thumbnail variants written:", sorted(p.name for p in out.glob("thumb_*.png")), "image usage:", g.usage)


if __name__ == "__main__":
    main()
