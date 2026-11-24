"""Background music (BGM): license-free procedural bed, Gemini Lyria provider, ducked mix into finished videos.

NOTE: the Lyria request/response shape below is UNVERIFIED until `music_live_test` has run against a real key.
"""
import base64
import os
import subprocess
import tempfile
from pathlib import Path

from . import gemini
from .errors import NotConnected

RATE = 44100
LYRIA_MODELS = ("lyria-3-clip-preview", "lyria-3-pro-preview", "lyria-3.5")


def _run(cmd):
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{cmd[0]} failed: {(e.stderr or '')[-400:]}") from e


def probe_duration(path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return round(float(out.strip()), 3)


def bgm_prompt(genre: str, lang: str = "en", mood: str = "calm") -> str:
    g = (genre or "").lower()
    if "histor" in g or "document" in g:
        style = "subtle ambient strings and low drones, slow and spacious"
    elif "advice" in g or "life" in g or "self" in g:
        style = "soft warm piano and gentle pads, slow tempo"
    else:
        style = f"soft ambient pads and light textures fitting a {genre or 'general'} video"
    return (f"Compose an INSTRUMENTAL background music track: {style}. Mood: {mood}. "
            "No vocals, no lyrics, no spoken words. Loop-friendly with a steady, seamless texture, no big dynamic changes, "
            "low intensity and non-distracting so that a narrator's voice stays fully intelligible on top of it. "
            "Original composition, not imitating any existing song or artist.")


# ---------------------------------------------------------------- procedural bed
_CHORDS = {  # Hz of pad partials
    "calm": [110.0, 164.81, 220.0, 329.63],         # A2 E3 A3 E4 (open fifths)
    "warm": [98.0, 146.83, 196.0, 246.94, 293.66],  # G major pad
    "tense": [82.41, 116.54, 164.81, 233.08],       # E2 Bb2 E3 Bb3 (tritone)
}


class ProceduralBed:
    """Ambient bed from ffmpeg lavfi only: layered sine pads, slow tremolo, chorus, faint filtered noise, low-pass. Deterministic."""

    def __init__(self, kind="calm"):
        if kind not in _CHORDS:
            raise ValueError(f"kind must be one of {sorted(_CHORDS)}")
        self.kind = kind

    def render(self, duration: float, out_path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        freqs = _CHORDS[self.kind]
        d = f"{float(duration):.3f}"
        cmd = ["ffmpeg", "-y", "-v", "error"]
        chains = []
        for i, f in enumerate(freqs):
            cmd += ["-f", "lavfi", "-t", d, "-i", f"sine=f={f}:r={RATE}"]
            rate = 0.11 + 0.04 * i  # slow, unsynchronised tremolo per voice
            chains.append(f"[{i}:a]volume=0.5,tremolo=f={rate:.2f}:d=0.6[v{i}]")
        n = len(freqs)
        cmd += ["-f", "lavfi", "-t", d, "-i", f"anoisesrc=d={d}:c=pink:r={RATE}:a=0.05:seed=7"]
        chains.append(f"[{n}:a]lowpass=f=500,volume=0.4[nz]")
        mix_in = "".join(f"[v{i}]" for i in range(n)) + "[nz]"
        chains.append(f"{mix_in}amix=inputs={n + 1}:normalize=0,volume=0.5,chorus=0.5:0.9:55|65:0.4|0.3:0.25|0.3:2|2.5,"
                      f"lowpass=f=1800,aformat=sample_fmts=s16:sample_rates={RATE}:channel_layouts=stereo,"
                      f"afade=t=in:d=0.5,afade=t=out:st={max(0.0, float(duration) - 0.5):.3f}:d=0.5[o]")
        cmd += ["-filter_complex", ";".join(chains), "-map", "[o]", "-t", d, "-c:a", "pcm_s16le", str(out_path)]
        _run(cmd)
        return out_path

    def describe(self):
        return dict(stage="music", status="done", note="procedural ambient bed (no external service, no copyright)")


# ---------------------------------------------------------------- Lyria
def _extend(src: Path, duration: float, out_path: Path):
    """Loop the clip with 1.5 s crossfades until it covers `duration`, trim, write stereo 44.1k wav."""
    clip = probe_duration(src)
    xf = 1.5
    fmt = f"aformat=sample_fmts=s16:sample_rates={RATE}:channel_layouts=stereo"
    if clip >= duration or clip <= 2 * xf + 0.5:
        # long enough, or too short to crossfade: plain loop
        _run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-t", f"{duration:.3f}",
              "-af", fmt, "-c:a", "pcm_s16le", str(out_path)])
        return
    reps = int((duration - xf) // (clip - xf)) + 2
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for _ in range(reps):
        cmd += ["-i", str(src)]
    chain, prev = [], "[0:a]"
    for i in range(1, reps):
        chain.append(f"{prev}[{i}:a]acrossfade=d={xf}[x{i}]")
        prev = f"[x{i}]"
    chain.append(f"{prev}{fmt}[o]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[o]", "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", str(out_path)]
    _run(cmd)


class LyriaMusic:
    """Gemini music generation via generateContent. API shape UNVERIFIED until music_live_test ran."""

    def __init__(self, model=None, session=None):
        self.model = model or os.environ.get("STUDIO_GEMINI_MUSIC_MODEL") or LYRIA_MODELS[0]
        self.session = session
        self.last_usage = {}
        self.last_mime = ""

    def _request(self, prompt):
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["AUDIO"]}}
        try:
            return gemini.generate_content(self.model, body, self.session)
        except gemini.GeminiError as e:
            if "HTTP 400" not in str(e):
                raise
            return gemini.generate_content(self.model, {"contents": body["contents"]}, self.session)

    def generate_clip(self, prompt, out_path) -> Path:
        """Raw clip as returned by the model, decoded to wav. Records mime type and usage."""
        resp = self._request(prompt)
        self.last_usage = gemini.usage(resp)
        for p in gemini._parts(resp):
            d = p.get("inlineData") or p.get("inline_data")
            if not (d and d.get("data")):
                continue
            mime = d.get("mimeType") or d.get("mime_type") or ""
            self.last_mime = mime
            raw = base64.b64decode(d["data"])
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as td:
                if mime.lower().startswith("audio/l16"):
                    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
                    ch = int(mime.split("channels=")[1].split(";")[0]) if "channels=" in mime else 1
                    f = Path(td) / "in.pcm"
                    f.write_bytes(raw)
                    pre = ["-f", "s16le", "-ar", str(rate), "-ac", str(ch)]
                else:
                    ext = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav",
                           "audio/ogg": ".ogg"}.get(mime.split(";")[0].lower(), ".bin")
                    f = Path(td) / ("in" + ext)
                    f.write_bytes(raw)
                    pre = []
                _run(["ffmpeg", "-y", "-v", "error", *pre, "-i", str(f), "-c:a", "pcm_s16le", str(out_path)])
            return out_path
        raise gemini.GeminiError("response contained no audio")

    def render(self, duration: float, out_path, prompt=None) -> Path:
        gemini.api_key()  # NotConnected if missing
        out_path = Path(out_path)
        with tempfile.TemporaryDirectory() as td:
            clip = self.generate_clip(prompt or bgm_prompt("general", "en", "calm"), Path(td) / "clip.wav")
            _extend(clip, float(duration), out_path)
        return out_path

    def describe(self):
        if os.environ.get("GEMINI_API_KEY", "").strip():
            return dict(stage="music", status="done", note=f"Gemini {self.model} (API shape unverified until music_live_test)")
        return dict(stage="music", status="not_connected", note="set GEMINI_API_KEY")


# ---------------------------------------------------------------- mixing
def mix_bgm(video_in, bgm_wav, video_out, bgm_db=-20, duck=True) -> Path:
    """Mix BGM under the video's narration. `bgm_db` = integrated loudness (LUFS) of the BGM before ducking.
    Ducking: sidechaincompress keyed by the narration (about -12 dB while speech is present, ~0.6 s release)."""
    video_in, video_out = Path(video_in), Path(video_out)
    dur = probe_duration(video_in)
    fo = max(0.0, dur - 2.0)
    bgm = (f"[1:a]aformat=channel_layouts=stereo,aresample={RATE},loudnorm=I={bgm_db}:TP=-3:LRA=7,aresample={RATE},"
           f"atrim=0:{dur:.3f},afade=t=in:d=1.5,afade=t=out:st={fo:.3f}:d=2.0[bg]")
    if duck:
        graph = [bgm, f"[0:a]aformat=channel_layouts=stereo,aresample={RATE},asplit=2[sp][sc]",
                 "[bg][sc]sidechaincompress=threshold=0.01:ratio=10:attack=20:release=600:makeup=1[bd]",
                 "[sp][bd]amix=inputs=2:duration=first:normalize=0[m]"]
    else:
        graph = [bgm, f"[0:a]aformat=channel_layouts=stereo,aresample={RATE}[sp]",
                 "[sp][bg]amix=inputs=2:duration=first:normalize=0[m]"]
    graph.append(f"[m]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad,atrim=0:{dur:.3f}[a]")
    video_out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video_in), "-i", str(bgm_wav), "-filter_complex", ";".join(graph),
          "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(video_out)])
    return video_out


def add_bgm(project_dir, provider=None, prompt=None, kind=None, filename=None, genre="general", lang="en", mood="calm") -> dict:
    """Write <name>_bgm.mp4 next to the narration-only file (never overwritten). Provider default: Lyria if a key is set, else procedural."""
    project_dir = Path(project_dir)
    if filename:
        src = project_dir / filename
    else:
        src = project_dir / "final.mp4"
        if not src.exists() and (project_dir / "short.mp4").exists():
            src = project_dir / "short.mp4"
    if not src.exists():
        raise FileNotFoundError(f"{src.name} not found in {project_dir}")
    dur = probe_duration(src)
    prompt = prompt or bgm_prompt(genre, lang, mood)
    if provider is None:
        provider = LyriaMusic() if os.environ.get("GEMINI_API_KEY", "").strip() else ProceduralBed(kind or "calm")
    bed = project_dir / "bgm_bed.wav"
    try:
        if isinstance(provider, LyriaMusic):
            provider.render(dur, bed, prompt=prompt)
            used = f"lyria:{provider.model}"
        else:
            provider.render(dur, bed)
            used = f"procedural:{getattr(provider, 'kind', '')}"
    except (NotConnected, gemini.GeminiError, RuntimeError):
        if not isinstance(provider, LyriaMusic):
            raise
        fb = ProceduralBed(kind or "calm")
        fb.render(dur, bed)
        used = f"procedural:{fb.kind} (fallback after Lyria failure)"
    out = project_dir / f"{src.stem}_bgm.mp4"
    mix_bgm(src, bed, out)
    return {"file": out.name, "provider": used, "seconds": probe_duration(out)}
