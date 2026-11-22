"""Voice stage: narration wav per section, durations measured with ffprobe."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from .errors import NotConnected

CHARS_PER_SEC = {"ja": 5.5, "en": 15.0}   # ja measured with real VOICEVOX 2026-11-22
SAMPLE_RATE = 24000


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def probe_duration(path: Path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return round(float(out.strip()), 3)


class VoiceProvider(Protocol):
    def synthesize(self, text: str, lang: str, out_path: Path) -> float: ...
    def describe(self) -> dict: ...


class MockVoice:
    """Silent track, length proportional to text length. Never a real voice."""

    def synthesize(self, text, lang, out_path):
        secs = max(0.5, len(text) / CHARS_PER_SEC.get(lang, CHARS_PER_SEC["en"]))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
              "-t", f"{secs:.3f}", "-c:a", "pcm_s16le", str(out_path)])
        return probe_duration(out_path)

    def describe(self):
        return dict(stage="voice", status="mock", note="MockVoice: silent audio, length from text size; not real narration")


def split_sentences(text: str) -> list[str]:
    parts = re.findall(r"[^。！？!?\n]+[。！？!?]?", text)
    return [p.strip() for p in parts if p.strip()]


class VoicevoxVoice:
    """Local VOICEVOX engine (HTTP). Unit-tested with a fake session only; not verified against a real engine."""

    def __init__(self, base_url=None, speaker=None, session=None, timeout=60):
        self.base_url = (base_url or os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")).rstrip("/")
        self.speaker = int(speaker if speaker is not None else os.environ.get("VOICEVOX_SPEAKER", 3))
        self.timeout = timeout
        if session is None:
            import requests
            session = requests.Session()
        self.session = session

    def _post(self, path, **kw):
        import requests
        try:
            r = self.session.post(self.base_url + path, timeout=self.timeout, **kw)
            r.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as e:
            raise NotConnected(f"VOICEVOX engine unreachable at {self.base_url} "
                               f"(start the engine or set VOICEVOX_URL; speaker via VOICEVOX_SPEAKER): {type(e).__name__}") from e
        return r

    def _one(self, sentence):
        q = self._post("/audio_query", params={"text": sentence, "speaker": self.speaker})
        return self._post("/synthesis", params={"speaker": self.speaker}, json=q.json()).content

    def synthesize(self, text, lang, out_path):
        sentences = split_sentences(text) or [text]
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            files = []
            for i, sent in enumerate(sentences):
                f = Path(td) / f"s{i:03d}.wav"
                f.write_bytes(self._one(sent))
                files.append(f)
            lst = Path(td) / "list.txt"
            lst.write_text("".join(f"file '{f}'\n" for f in files))
            _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                  "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(out_path)])
        return probe_duration(out_path)

    def describe(self):
        return dict(stage="voice", status="not_connected",
                    note=f"VoicevoxVoice: needs a running VOICEVOX engine at {self.base_url}; not verified against a real engine")


class EnglishVoice:
    """TODO: English TTS. The provider (OpenAI / ElevenLabs) API must be written from its current docs and verified with a real key."""

    def synthesize(self, text, lang, out_path):
        raise NotConnected("set OPENAI_API_KEY or ELEVENLABS_API_KEY and implement EnglishVoice from the provider's current docs")

    def describe(self):
        return dict(stage="voice", status="not_connected", note="EnglishVoice: stub, set OPENAI_API_KEY or ELEVENLABS_API_KEY")


def render_voice(project_dir: Path, provider: VoiceProvider, lang: str) -> dict:
    project_dir = Path(project_dir)
    script = json.loads((project_dir / "script.json").read_text(encoding="utf-8"))
    out = project_dir / "voice"
    out.mkdir(parents=True, exist_ok=True)
    durations = {}
    for i, sec in enumerate(script["sections"], 1):
        key = f"{i:02d}"
        durations[key] = provider.synthesize(sec["narration"], lang, out / f"section_{key}.wav")
    (out / "durations.json").write_text(json.dumps(durations, indent=1))
    return durations


def describe(provider: VoiceProvider) -> dict:
    return provider.describe()
