"""Live check of Lyria music models (needs GEMINI_API_KEY) plus the procedural beds. Files go to work/gemini_live/. Never prints the key."""
import time
from pathlib import Path

from . import music
from .errors import NotConnected


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    prompt = music.bgm_prompt("history documentary", "en", "calm")
    for kind in ("calm", "warm", "tense"):
        p = music.ProceduralBed(kind).render(20, out / f"bed_{kind}.wav")
        print("procedural", kind, "ok", music.probe_duration(p), "s")
    ok = 0
    for model in music.LYRIA_MODELS:
        m = music.LyriaMusic(model)
        t = time.time()
        try:
            p = m.render(20, out / f"lyria_{model}.wav", prompt=prompt)
            ok += 1
            print(f"lyria {model}: ok | mime: {m.last_mime} | seconds: {music.probe_duration(p)} | took: {round(time.time() - t, 1)} | usage: {m.last_usage}")
        except NotConnected as e:
            print(f"lyria {model}: FAIL not connected: {e}")
            break
        except Exception as e:  # noqa: BLE001
            print(f"lyria {model}: FAIL {type(e).__name__}: {str(e)[:300]} | mime: {m.last_mime}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
