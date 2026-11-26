"""Real-footage short editor (salon use): phone clips -> one 1080x1920 short with telops + a closing call-to-action card.

Deterministic ffmpeg only (no API calls, no cost). Reuses edit._run / edit.make_short_ass. Silent output by default
(original audio is dropped unless keep_audio=True; add licensed BGM in Instagram if wanted).

spec (JSON/dict):
  {"clips": [{"path": "a.mp4", "start": 0, "end": 8, "speed": 1.0}, ...],
   "telops": [{"at": 0.0, "dur": 3.0, "text": "..."}],        # times are on the OUTPUT timeline
   "cta": "ご予約はDMかお電話へ", "cta_seconds": 2.5, "out": "short.mp4"}
Usage: python -m studio.footage_short spec.json
"""
import json
import sys
import tempfile
from pathlib import Path

from .edit import FONTS_DIR, _ass_ts, _run, make_short_ass, probe_duration

W, H = 1080, 1920
MAX_SECONDS = 59.0


def _prep(clip, i, tmp, keep_audio):
    """Trim, speed-change and cover-crop one clip to 1080x1920 @30fps."""
    start, end, speed = float(clip.get("start", 0)), clip.get("end"), float(clip.get("speed", 1.0))
    out = tmp / f"c{i:02d}.mp4"
    if Path(str(clip["path"])).suffix.lower() in (".png", ".jpg", ".jpeg"):   # still image -> slow push-in
        dur = float(clip.get("seconds", 2.5))
        n = max(1, round(dur * 30))
        vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
              f"zoompan=z='1+{float(clip.get('zoom', 0.08))}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,format=yuv420p")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", f"{dur}", "-i", str(clip["path"]), "-vf", vf,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", str(out)])
        return out
    vf = f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}"]
    if end is not None:
        cmd += ["-t", f"{float(end) - start}"]
    cmd += ["-i", str(clip["path"]), "-vf", vf]
    cmd += ["-af", f"atempo={speed}", "-c:a", "aac"] if keep_audio else ["-an"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)]
    _run(cmd)
    return out


def _cta_clip(text, seconds, tmp):
    out = tmp / "cta.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x2f3237:s={W}x{H}:r=30:d={seconds}",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])
    return out


def build(spec):
    clips, keep_audio = spec["clips"], bool(spec.get("keep_audio", False))
    cta, cta_s = spec.get("cta", ""), float(spec.get("cta_seconds", 2.5))
    out = Path(spec.get("out", "short.mp4")).resolve()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        parts = [_prep(c, i, tmp, keep_audio) for i, c in enumerate(clips)]
        body = sum(probe_duration(p) for p in parts)
        total = body + (cta_s if cta else 0)
        if total > MAX_SECONDS:
            raise ValueError(f"short is {total:.1f}s; limit {MAX_SECONDS:.0f}s")
        if cta:
            parts.append(_cta_clip(cta, cta_s, tmp))
        xf = float(spec.get("xfade", 0))   # crossfade seconds between scenes (0 = hard cuts)
        durs = [probe_duration(p) for p in parts]
        if xf > 0:
            total = sum(durs) - (len(parts) - 1) * xf
            body = (total - cta_s + xf) if cta else total   # CTA text starts once its fade-in has finished
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        events = [(float(x["at"]), float(x["at"]) + float(x["dur"]), x["text"]) for x in spec.get("telops", [])]
        top_texts = [x["text"] for x in spec.get("telops", []) if x.get("style") == "top"]
        if cta:
            events.append((body, total, cta))
        ass = tmp / "short.ass"
        text = make_short_ass(events, "IPAGothic", font_px=84)
        if cta:   # closing card: centred and larger (ASS override tags; make_short_ass escapes braces itself)
            text = text.replace(f",,0,0,0,,{cta}", f",,0,0,0,,{{\\an5\\fs96}}{cta}")
        for tt in top_texts:   # small label at the top (e.g. "image video, AI-generated")
            text = text.replace(f",,0,0,0,,{tt}", f",,0,0,0,,{{\\an8\\fs44}}{tt}")
        ass.write_text(text, "utf-8")
        vf = f"subtitles={ass.name}:fontsdir={FONTS_DIR},format=yuv420p"
        enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart"]
        audio = ["-c:a", "aac", "-b:a", "128k"] if keep_audio else ["-an"]
        if xf > 0 and len(parts) > 1:
            ins = [x for p in parts for x in ("-i", str(p))]
            chain, last, acc = [], "[0:v]", durs[0]
            for k in range(1, len(parts)):
                off = acc - k * xf
                lab = f"[x{k}]"
                chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={xf}:offset={off:.3f}{lab}")
                last, acc = lab, acc + durs[k]
            fc = ";".join(chain) + f";{last}{vf}[o]"
            _run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[o]", *enc, "-an", str(out)], cwd=tmp)
        else:
            _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf, *enc, *audio, str(out)], cwd=tmp)
    return out


if __name__ == "__main__":
    import os
    spec_path = Path(sys.argv[1]).resolve()
    os.chdir(spec_path.parent)   # clip paths and "out" are relative to the spec file
    print(build(json.loads(spec_path.read_text(encoding="utf-8"))))
