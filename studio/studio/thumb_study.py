"""Download the public thumbnails of reference videos listed in thumb_ids.txt and build numbered contact sheets for analysis.
No API key needed (public thumbnail URLs). Images are only looked at to learn composition patterns; they are not reused or redistributed."""
from pathlib import Path

import requests
from PIL import Image, ImageDraw

IDS = Path(__file__).with_name("thumb_ids.txt")


def fetch(vid):
    for name in ("maxresdefault", "hqdefault"):
        r = requests.get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=30)
        if r.status_code == 200 and len(r.content) > 5000:
            import io
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    return None


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    ids = [x.strip() for x in IDS.read_text().split() if x.strip()]
    tiles = []
    for i, v in enumerate(ids, 1):
        im = fetch(v)
        print(i, v, "ok" if im else "FAILED")
        if im:
            im = im.resize((480, 270))
            ImageDraw.Draw(im).rectangle((0, 0, 44, 30), fill=(0, 0, 0))
            ImageDraw.Draw(im).text((6, 8), str(i), fill=(255, 255, 255))
            tiles.append(im)
    for s in range(0, len(tiles), 12):
        chunk = tiles[s:s + 12]
        sheet = Image.new("RGB", (480 * 3, 270 * 4), (20, 20, 20))
        for k, t in enumerate(chunk):
            sheet.paste(t, ((k % 3) * 480, (k // 3) * 270))
        sheet.save(out / f"channel_thumbsheet_{s // 12 + 1}.png")
    print("sheets written")


if __name__ == "__main__":
    main()
