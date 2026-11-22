"""Gemini TTS comparison (needs GEMINI_API_KEY): the same Japanese sentences read by several prebuilt male voices with a style direction."""
import sys
import time
import wave
from pathlib import Path

from . import gemini

MODEL_DEFAULT = "gemini-3.8-flash-tts"
TEXT = "お相手の話に、ゆっくりと耳を傾けてみましょう。言葉の合間にある小さな間や笑顔が、二人の距離を少しずつ近づけてくれます。"
STYLE = ("Read the following Japanese text as a calm, warm, trustworthy middle-aged Japanese male narrator talking naturally to a friend. "
         "Moderately slow pace, natural pauses and breathing, gentle intonation, no theatrical acting, no announcer tone.")
VOICES = ["Charon", "Orus", "Iapetus", "Umbriel", "Algieba", "Schedar", "Alnilam", "Sadaltager"]


def write_wav(path, pcm, rate):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return len(pcm) / 2 / rate


def main():
    import os
    model = os.environ.get("STUDIO_GEMINI_TTS_MODEL", MODEL_DEFAULT)
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, v in enumerate(VOICES, 1):
        t = time.time()
        try:
            pcm, rate, u = gemini.tts(model, TEXT, v, STYLE)
            sec = write_wav(out / f"tts_{i:02d}_{v}.wav", pcm, rate)
            print(f"OK {v} | model={model} | audio_seconds={sec:.1f} | wall={time.time() - t:.1f}s | rate={rate} | usage={u}"); ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {v} | {type(e).__name__}: {str(e)[:220]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
