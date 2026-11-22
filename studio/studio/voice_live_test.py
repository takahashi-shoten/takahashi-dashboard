"""Live check of VoicevoxVoice against a real VOICEVOX engine. Run: python -m studio.voice_live_test

Prints MEASURED facts as `key: value` lines. Exits non-zero if the engine is unreachable.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from .errors import NotConnected
from .voice import VoicevoxVoice

SAMPLE = ("四十歳を過ぎてからの恋愛は、若いころとは少し違います。"
          "相手に完璧を求めるよりも、お互いの生活や時間を大切にできることが、何より大事になってきます。"
          "焦らず、自分らしさを忘れずに、ゆっくりと関係を育てていきましょう。"
          "新しい出会いは、思いがけない場所で、ふとしたきっかけから始まるものです。")
OUT = Path(__file__).resolve().parent.parent / "work" / "voicevox_live" / "sample.wav"


def speaker_name(speakers, speaker_id):
    """Return (speaker name, style name) for a style id from /speakers JSON, or (None, None)."""
    for sp in speakers:
        for st in sp.get("styles", []):
            if st.get("id") == speaker_id:
                return sp.get("name"), st.get("name")
    return None, None


def chars_per_sec(text, duration):
    return len(text) / duration if duration > 0 else 0.0


def probe_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                          "stream=sample_rate,channels", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["sample_rate"]), int(s["channels"])


def main():
    import requests
    v = VoicevoxVoice(timeout=120)
    try:
        version = v.session.get(v.base_url + "/version", timeout=10).json()
        speakers = v.session.get(v.base_url + "/speakers", timeout=30).json()
        t0 = time.monotonic()
        dur = v.synthesize(SAMPLE, "ja", OUT)
        wall = time.monotonic() - t0
    except (NotConnected, requests.RequestException) as e:
        print(f"FAIL: VOICEVOX engine unreachable or request failed at {v.base_url}: {e}", file=sys.stderr)
        return 1
    rate, ch = probe_audio(OUT)
    name, style = speaker_name(speakers, v.speaker)
    print(f"engine_url: {v.base_url}")
    print(f"engine_version: {version}")
    print(f"speaker_count: {len(speakers)}")
    print(f"speaker_id_used: {v.speaker}")
    print(f"speaker_name: {name}")
    print(f"speaker_style: {style}")
    print(f"sample_chars: {len(SAMPLE)}")
    print(f"duration_sec: {dur:.3f}")
    print(f"synthesis_wall_sec: {wall:.3f}")
    print(f"real_time_factor: {wall / dur:.3f}")
    print(f"chars_per_sec: {chars_per_sec(SAMPLE, dur):.2f} (project assumption: 6.5)")
    print(f"file_size_bytes: {OUT.stat().st_size}")
    print(f"sample_rate_hz: {rate}")
    print(f"channels: {ch}")
    print(f"output: {OUT}")
    if name is None:
        print(f"FAIL: speaker id {v.speaker} not found in /speakers", file=sys.stderr)
        return 1
    print(f"VOICEVOX credit required in video description: VOICEVOX:{name} (style: {style})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
