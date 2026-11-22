"""Why was English TTS ~3x slower than expected? Same English sentences, several directions / voices / models; prints audio seconds per char."""
import sys
import time
from pathlib import Path

from . import gemini
from .tts_compare import write_wav

TEXT = "How did ancient humans first make fire? Here's the twist: for ages, they probably didn't."
CASES = [
    ("plain_iapetus_3.8", "gemini-3.8-flash-tts", "Iapetus", ""),
    ("brisk_iapetus_3.8", "gemini-3.8-flash-tts", "Iapetus",
     "Read the following as an engaged, natural male narrator telling a friend a surprising fact in a short video. Brisk conversational pace, short pauses only between sentences."),
    ("say_fast_iapetus_3.8", "gemini-3.8-flash-tts", "Iapetus", "Say quickly and energetically:"),
    ("plain_charon_3.8", "gemini-3.8-flash-tts", "Charon", ""),
    ("plain_iapetus_3.1", "gemini-3.1-flash-tts-preview", "Iapetus", ""),
    ("plain_iapetus_2.5", "gemini-2.5-flash-preview-tts", "Iapetus", ""),
]


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    for name, model, voice, style in CASES:
        t = time.time()
        try:
            pcm, rate, u = gemini.tts(model, TEXT, voice, style)
            sec = write_wav(out / f"en_{name}.wav", pcm, rate)
            print(f"OK {name} | chars={len(TEXT)} audio_seconds={sec:.1f} chars_per_sec={len(TEXT) / sec:.1f} | wall={time.time() - t:.1f}s | usage={u}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name} | {type(e).__name__}: {str(e)[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
