"""Gemini TTS: the owner's three favourite voices x several delivery directions, on a longer realistic passage."""
import os
import sys
import time
from pathlib import Path

from . import gemini
from .tts_compare import write_wav

MODEL_DEFAULT = "gemini-3.8-flash-tts"
TEXT = ("「仕事、大変なんですよ」と言われて、「転職を考えたら？」と返したなら、その瞬間、相手の心のシャッターが少し下りたかもしれません。"
        "悪気はないんです。ただ、答えを出したくなる。それは、長く働いてきた人の、立派な習慣でもあります。")
BASE = ("Read the following Japanese text as a middle-aged Japanese male narrator talking to a friend. "
        "Natural spoken Japanese, no announcer tone, no theatrical acting. ")
STYLES = {
    "calm": BASE + "Very calm and unhurried, soft-spoken, thoughtful pauses between phrases.",
    "warm": BASE + "Warm and friendly, a faint smile in the voice, relaxed conversational pace, like talking over coffee.",
    "low": BASE + "Slightly lower and steady, gentle and intimate, as if speaking quietly to one person, slow pace.",
    "human": BASE + "Casual and unpolished, like someone thinking aloud: small natural hesitations, audible breaths, uneven rhythm, "
                    "slight emphasis on key words, not perfectly smooth.",
}
VOICES = [("Iapetus", 3), ("Alnilam", 7), ("Charon", 1)]


def main():
    model = os.environ.get("STUDIO_GEMINI_TTS_MODEL", MODEL_DEFAULT)
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for voice, num in VOICES:
        for key, style in STYLES.items():
            t = time.time()
            try:
                pcm, rate, u = gemini.tts(model, TEXT, voice, style)
                sec = write_wav(out / f"v_{voice}_{key}.wav", pcm, rate)
                print(f"OK {voice} {key} | audio_seconds={sec:.1f} | chars_per_sec={len(TEXT) / sec:.2f} | wall={time.time() - t:.1f}s | usage={u}"); ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {voice} {key} | {type(e).__name__}: {str(e)[:200]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
