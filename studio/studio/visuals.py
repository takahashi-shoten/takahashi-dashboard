"""Visuals stage: one 1920x1080 PNG per section, with a prompt safety pre-filter."""
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from .errors import NotConnected

FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


class ImageProvider(Protocol):
    def generate(self, prompt: str, out_path: Path, size=(1920, 1080)) -> None: ...
    def describe(self) -> dict: ...


def _font(px):
    try:
        return ImageFont.truetype(FONT, px)
    except OSError:
        return ImageFont.load_default()


class MockImage:
    def generate(self, prompt, out_path, size=(1920, 1080)):
        h = hashlib.sha256(prompt.encode("utf-8")).digest()
        c1, c2 = tuple(h[0:3]), tuple(h[3:6])
        w, ht = size
        img = Image.new("RGB", size)
        d = ImageDraw.Draw(img)
        for y in range(ht):
            t = y / max(1, ht - 1)
            d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
        m = min(w, ht)
        d.text((w // 2, ht // 2), "MOCK", font=_font(m // 4), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        d.text((40, ht - 40), prompt[:60], font=_font(m // 22), fill=(255, 255, 255), anchor="ls", stroke_width=2, stroke_fill=(0, 0, 0))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG")

    def describe(self):
        return dict(stage="visuals", status="mock", note="MockImage: gradient + MOCK watermark; not a real asset")


class _KeyedStub:
    env = ""
    name = ""

    def generate(self, prompt, out_path, size=(1920, 1080)):
        if not os.environ.get(self.env):
            raise NotConnected(f"set {self.env} to use {self.name}")
        # TODO: write the API call from the provider's current docs and verify it with a real key.
        # No endpoint/parameters are guessed here on purpose.
        raise NotConnected(f"{self.name}: {self.env} is set but the API call is not implemented yet")

    def describe(self):
        return dict(stage="visuals", status="not_connected", note=f"{self.name}: stub, needs {self.env} and an implementation")


def aspect_ratio(size):
    """Gemini imageConfig.aspectRatio for a pixel size: 16:9 landscape, 9:16 portrait, 1:1 square."""
    w, h = size
    return "16:9" if w > h else "9:16" if h > w else "1:1"


class GeminiImage:
    """Gemini image generation over REST (model ids come from the live models list; see key-check workflow output).
    Verified only by studio/gemini_live_test.py with a real key. Records token usage in `last_usage` (price: check the Google pricing page)."""
    name = "GeminiImage"

    STYLES = {
        "manga": ("Japanese comic (manga) illustration, clean bold line art, flat bright colours, expressive exaggerated faces and emotions. "
                  "No text, letters, speech bubbles, logos or brand names anywhere. Fictional characters only."),
        "illustration": "Original illustration. No text, letters, logos or watermarks. No real people.",
        "photo": ("Photorealistic photograph, natural lighting, realistic skin texture and proportions. Fictional people only (not any real person's "
                  "likeness). No text, letters, logos or watermarks."),
    }

    def __init__(self, model=None, session=None, style="illustration"):
        self.model = model or os.environ.get("STUDIO_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
        self.session, self.last_usage, self.style = session, None, style
        self.usage = []     # one entry per generated image (list.append is thread-safe)

    def generate(self, prompt, out_path, size=(1920, 1080)):
        import io
        from PIL import Image, ImageOps
        from . import gemini
        text = f"{prompt}\n\n{self.STYLES[self.style]}"
        attempts = [{"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect_ratio(size)}}, {"responseModalities": ["TEXT", "IMAGE"]}]
        last = None
        for cfg in attempts:                      # some models need TEXT+IMAGE or reject imageConfig: try the simplest alternative once
            try:
                resp = gemini.generate_content(self.model, {"contents": [{"parts": [{"text": text}]}], "generationConfig": cfg}, self.session)
            except gemini.GeminiError as e:
                last = e
                if "HTTP 400" in str(e):
                    continue
                raise
            img = gemini.first_image(resp)
            if img:
                self.last_usage = gemini.usage(resp)
                self.usage.append(self.last_usage)
                im = ImageOps.fit(Image.open(io.BytesIO(img[1])).convert("RGB"), size, method=Image.LANCZOS)
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                im.save(out_path, "PNG")
                return
            last = gemini.GeminiError("response contained no image")
        raise last

    def describe(self):
        ok = bool(os.environ.get("GEMINI_API_KEY"))
        return dict(stage="visuals", status="done" if ok else "not_connected",
                    note=f"GeminiImage {self.model} via REST" + ("" if ok else " (needs GEMINI_API_KEY)"))


class OpenAIImage(_KeyedStub):
    env, name = "OPENAI_API_KEY", "OpenAIImage"


# --- prompt safety pre-filter: simple and conservative; a human still reviews outputs ---
SEXUAL = ["nude", "naked", "nsfw", "porn", "erotic", "sexual", "hentai", "topless", "ヌード", "裸", "エロ", "ポルノ", "性行為"]
MINOR = ["child", "kid", "minor", "underage", "schoolgirl", "schoolboy", "loli", "shota", "teen", "子供", "子ども", "少女", "少年", "未成年", "ロリ", "ショタ", "女子高生"]
SEXUAL_CONTEXT = ["sexy", "sensual", "seductive", "lingerie", "swimsuit", "bikini", "セクシー", "水着", "下着"]
CHARACTERS = ["mickey mouse", "minnie mouse", "donald duck", "pikachu", "pokemon", "mario", "luigi", "zelda", "doraemon", "hello kitty",
              "naruto", "goku", "luffy", "spider-man", "spiderman", "batman", "superman", "elsa", "mickey",
              "ミッキー", "ピカチュウ", "ポケモン", "マリオ", "ドラえもん", "ハローキティ", "ナルト", "悟空", "ルフィ", "アンパンマン", "ちいかわ"]
PERSON_PATTERNS = [  # case-sensitive: a capitalised name must follow
    r"\b(?:photo|picture|portrait|image|likeness|photograph)\s+of\s+(?!A\b|An\b|The\b)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+",
    r"\b(?:looks?|looking|resembl\w+)\s+like\s+(?!A\b|An\b|The\b)[A-Z][a-z]+",
]
PERSON_WORDS = [r"\bdeepfake\b", r"\bcelebrity\b", r"\bfamous (?:actor|actress|singer|politician)\b",
                r"(?:の写真|そっくり|に似た|に似せ|の顔)", r"(?:有名人|芸能人|実在の人物)"]


def _has_word(w, low):
    return re.search(rf"\b{re.escape(w)}", low) if w.isascii() else w in low


def check_prompt(prompt: str) -> list[str]:
    low, reasons = prompt.lower(), []
    if any(re.search(p, prompt) for p in PERSON_PATTERNS) or any(re.search(p, low) for p in PERSON_WORDS):
        reasons.append("real-person name/likeness request")
    sexual = [w for w in SEXUAL if _has_word(w, low)]
    if sexual:
        reasons.append(f"sexual term: {sexual[0]}")
    minors = [w for w in MINOR if _has_word(w, low)]
    if minors and (sexual or any(_has_word(w, low) for w in SEXUAL_CONTEXT)):
        reasons.append(f"minor in sexual context: {minors[0]}")
    chars = [w for w in CHARACTERS if _has_word(w, low)]
    if chars:
        reasons.append(f"copyrighted character: {chars[0]}")
    return reasons


def render_visuals(project_dir: Path, provider: ImageProvider) -> list[Path]:
    project_dir = Path(project_dir)
    script = json.loads((project_dir / "script.json").read_text(encoding="utf-8"))
    bad = {f"{i:02d}": r for i, s in enumerate(script["sections"], 1) if (r := check_prompt(s["visual_prompt"]))}
    if bad:
        raise ValueError("visual_prompt rejected: " + "; ".join(f"section {k}: {', '.join(r)}" for k, r in bad.items()))
    out = project_dir / "visuals"
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, s in enumerate(script["sections"], 1):
        p = out / f"section_{i:02d}.png"
        provider.generate(s["visual_prompt"], p, (1920, 1080))
        paths.append(p)
    return paths


def describe(provider: ImageProvider) -> dict:
    return provider.describe()
