"""Image-to-video probe for the salon demo (needs GEMINI_API_KEY): animate ONE generated kimono image with Gemini Omni (Interactions API).
Tries a few request shapes for image input and stops at the first success (failures cost nothing; a success is ~0.07 USD/s at 720p).
Output: work/gemini_live/kitsuke_motion_<n>.mp4. Never prints the key. AI-generated mock footage only."""
import base64
import subprocess
import sys
import time
from pathlib import Path

import requests

from . import gemini
from .video_probe import find_video

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
NAMES = ["kitsuke_1_obi_hands.png", "kitsuke_2_back_view.png", "kitsuke_3_accessories.png", "kitsuke_4_finished_back.png"]
PROMPTS = {
    1: "Keep the scene, garment, colours and framing exactly as in the image. Subtle natural motion only: the dresser's hands adjust and tighten the bow at the back, "
       "fabric moves slightly, a slow gentle camera push-in. No faces. About 5 seconds, vertical 9:16, calm modern gray atmosphere.",
    4: "Keep the scene, garment, colours and framing exactly as in the image. Subtle natural motion only: the woman slowly turns her hand on the door frame, the hakama ribbon "
       "sways slightly, a slow gentle camera push-in. Face never visible. About 5 seconds, vertical 9:16, calm modern gray atmosphere.",
}


def load_image(name):
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    p = out / name
    if p.exists():
        return p.read_bytes()
    subprocess.run(["git", "fetch", "-q", "origin", "studio-samples"], check=True)
    return subprocess.run(["git", "show", f"origin/studio-samples:{name}"], check=True, capture_output=True).stdout


def shapes(b64, prompt):
    img = {"type": "image", "data": b64, "mime_type": "image/png"}
    rf = {"response_format": {"type": "video", "aspect_ratio": "9:16"}}
    return {
        "A_list_data": {"input": [{"type": "text", "text": prompt}, img], **rf},
        "B_list_inline": {"input": [{"type": "text", "text": prompt}, {"type": "image", "inline_data": {"data": b64, "mime_type": "image/png"}}], **rf},
        "C_content_wrap": {"input": [{"role": "user", "content": [{"type": "text", "text": prompt}, img]}], **rf},
    }


def main(n=1):
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    b64 = base64.b64encode(load_image(NAMES[n - 1])).decode()
    hdr = {"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"}
    for model in ["gemini-omni-1.1-flash", "gemini-omni-flash-preview"]:
        for label, body in shapes(b64, PROMPTS[n]).items():
            t = time.time()
            r = requests.post(URL, json={"model": model, **body}, headers=hdr, timeout=900)
            print(f"{model} [{label}] HTTP {r.status_code} in {round(time.time() - t, 1)}s")
            try:
                j = r.json()
            except ValueError:
                print("non-json", r.text[:200]); continue
            hit = find_video(j)
            if hit:
                (out / f"kitsuke_motion_{n}.mp4").write_bytes(base64.b64decode(hit[1]))
                print("VIDEO OK", model, label, "usage:", j.get("usage") or j.get("usageMetadata"))
                return 0
            print("no video:", str(j)[:350].replace(b64[:40], "<img>"))
    return 1


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
