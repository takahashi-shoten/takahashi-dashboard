"""Image-to-video probe for the salon demo (needs GEMINI_API_KEY): animate ONE generated kimono image with Gemini Omni (Interactions API).
Tries a few request shapes for image input and stops at the first success (failures cost nothing; a success is ~0.07 USD/s at 720p).
Output: work/gemini_live/kitsuke_motion_<n>.mp4. Never prints the key. AI-generated mock footage only."""
import base64
import sys
import time
from pathlib import Path

import requests

from . import gemini
from .video_probe import find_video

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
NAMES = {"1": "kitsuke_1_obi_hands.jpg", "2": "kitsuke_2_back_view.jpg", "3": "kitsuke_3_accessories.jpg", "4": "kitsuke_4_finished_back.jpg",
         "bf1a": "kitsuke_b_f1a.jpg", "bf2b": "kitsuke_b_f2b.jpg", "bf1b": "kitsuke_b_f1b.jpg", "f1": "kitsuke_f1_obi_hands.jpg", "f2": "kitsuke_f2_back_view.jpg", "f4": "kitsuke_f4_finished_back.jpg"}
ASSETS = Path(__file__).resolve().parent.parent / "assets" / "kitsuke_demo"
KEEP = ("Keep the scene, garment, colours, framing and the shape of every ribbon and bow exactly as in the image; no morphing, no sudden shape changes. "
        "Fabric behaves like real stiff silk with natural weight: it folds, settles and recovers slowly under gravity, with a subtle sheen. "
        "Slow, deliberate, human-speed movements. No faces. About 5 seconds, vertical 9:16, calm modern gray atmosphere.")
PROMPTS = {
    "1": "The dresser's hands gently settle and straighten the hakama bow once, slowly; the fabric of the bow and obi shifts a little and then rests naturally. A very slow, gentle camera push-in. " + KEEP,
    "2": "The dresser's hands lightly smooth and straighten the two wings of the back ribbon, then pause; the woman stands still and breathes quietly. The mirror reflection stays stable. A very slow camera push-in. " + KEEP,
    "3": "Still-life of folded kimono and accessories on the gray table. No hands. A very slow camera glide over the objects, soft window light shifting gently, the silk cords settle by a hair. " + KEEP,
    "4": "The woman stands still at the doorway, breathing quietly; one hand rests on the door frame; the hakama ribbon and pleats sway very slightly. A slow gentle camera push-in. Her face is never visible. " + KEEP,
}


CAMERA_ONLY = "Very slow camera push-in only. Nothing in the scene moves. Keep everything unchanged. 5 seconds, vertical 9:16."
SIMPLE = {
    "bf1b": "Subtle natural motion: the dresser's hands gently settle the layered obi wings at the back, once, slowly. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "bf1a": "Subtle natural motion: the dresser's hands gently shape and settle the layered obi wings at the back, once, slowly. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "bf2b": "Very slow camera push-in only. The woman and the obi stay perfectly still; the fabric does not move. Keep everything unchanged. 5 seconds, vertical 9:16.",
    "f1": "Subtle natural motion: the dresser's hands gently shape the obi bow at the back. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "f2": "Subtle natural motion: the dresser's hands lightly adjust the obi at the back. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "1": "Subtle natural motion: the dresser's hands gently settle the bow at the back. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "2": "Subtle natural motion: the dresser's hands lightly adjust the ribbon at the back. Slow camera push-in. Keep everything else unchanged. 5 seconds, vertical 9:16.",
    "3": "Very slow camera glide over the objects on the table with soft shifting light. Keep everything unchanged. 5 seconds, vertical 9:16.",
    "4": "Very slow camera push-in; the ribbon at the back sways slightly. Keep everything unchanged. 5 seconds, vertical 9:16.",
}


def load_image(name):
    return (ASSETS / name).read_bytes()


def shapes(b64, prompt):
    img = {"type": "image", "data": b64, "mime_type": "image/jpeg"}
    rf = {"response_format": {"type": "video", "aspect_ratio": "9:16"}}
    return {
        "A_list_data": {"input": [{"type": "text", "text": prompt}, img], **rf},
        "B_list_inline": {"input": [{"type": "text", "text": prompt}, {"type": "image", "inline_data": {"data": b64, "mime_type": "image/jpeg"}}], **rf},
        "C_content_wrap": {"input": [{"role": "user", "content": [{"type": "text", "text": prompt}, img]}], **rf},
    }


def main(ns=("1",)):
    rc = 0
    for n in ns:
        rc |= one(n)
    return rc


def one(n):
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    b64 = base64.b64encode(load_image(NAMES[n])).decode()
    hdr = {"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"}
    for model, prompt in [("gemini-omni-1.1-flash", PROMPTS.get(n) or SIMPLE[n]), ("gemini-omni-1.1-flash", SIMPLE[n]), ("gemini-omni-flash-preview", SIMPLE[n]), ("gemini-omni-1.1-flash", CAMERA_ONLY)]:
        for label, body in list(shapes(b64, prompt).items())[:1]:
            t = time.time()
            r = requests.post(URL, json={"model": model, **body}, headers=hdr, timeout=900)
            print(f"{model} [{label}] HTTP {r.status_code} in {round(time.time() - t, 1)}s")
            try:
                j = r.json()
            except ValueError:
                print("non-json", r.text[:200]); continue
            hit = find_video(j)
            if hit:
                (out / f"kitsuke_motion_v2_{n}.mp4").write_bytes(base64.b64decode(hit[1]))
                print("VIDEO OK", model, label, "usage:", j.get("usage") or j.get("usageMetadata"))
                return 0
            print("no video:", str(j)[:350].replace(b64[:40], "<img>"))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["1"]))
