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


JA_TEXTS = ["縄文時代の人々は、なぜ世界最古級の土器を作れたのでしょうか。", "約一万六千年前の土器が、青森県で見つかっています。", "それは、料理のためだった可能性があります。"]
JA_WARM = ("Read the following Japanese text as a middle-aged Japanese male narrator talking to a friend. Natural spoken Japanese, no announcer tone, no theatrical acting. "
           "Warm and friendly, a faint smile in the voice, relaxed conversational pace, like talking over coffee.")
JA_CASES = [("ja_plain", ""), ("ja_say_brisk", "Say naturally and briskly:"), ("ja_warm_long", JA_WARM), ("ja_say_warm", "Say in a warm, friendly, natural tone:")]


def ja_main(out):
    for name, style in JA_CASES:
        for i, text in enumerate(JA_TEXTS, 1):
            t = time.time()
            try:
                pcm, rate, u = gemini.tts("gemini-3.8-flash-tts", text, "Iapetus", style)
                sec = write_wav(out / f"{name}_{i}.wav", pcm, rate)
                print(f"OK {name} #{i} | chars={len(text)} audio_seconds={sec:.1f} chars_per_sec={len(text) / sec:.1f} | wall={time.time() - t:.1f}s")
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name} #{i} | {type(e).__name__}: {str(e)[:160]}")


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    ja_main(out)
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
