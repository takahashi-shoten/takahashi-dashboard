"""Edit stage: stills + narration -> final.mp4 / final.srt / shorts.mp4 / thumbnail.png (ffmpeg + Pillow, local only).

Project layout: script.json, voice/section_NN.wav, voice/durations.json, visuals/section_NN.png
(NN is 1-based, or 0-based if section_00 files exist).
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SHORT_PAUSE = 0.2      # tighter pause after each beat of a Short
SHORT_MAX = 59.0       # hard cap (seconds) for a Short
SHORT_SIZE = (1080, 1920)
CAPTION_WORDS = 5      # captions show 3-5 words at a time
PAUSE = 0.4            # silence appended after each section's narration
HOOK_MAX = 55.0        # seconds of final video used for shorts
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
FONTS_DIR = str(Path(FONT).parent)
JA_MAX, EN_MAX = 22, 42


def describe():
    return dict(stage="edit", status="done", note="ffmpeg assembly, SRT, shorts, thumbnail (deterministic, tested locally)")


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-1500:]}")
    return r.stdout


def probe_duration(path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


def span(duration, fps=30) -> float:
    """Length of one section in the video: narration + pause, quantized to whole frames."""
    return round((duration + PAUSE) * fps) / fps


# ---------- subtitles ----------
def _is_ja(text):
    return sum(ord(c) > 0x2E80 for c in text) > len(text) / 4


def split_lines(text):
    text = " ".join(text.split())
    if _is_ja(text):
        lines = []
        for piece in re.findall(r"[^、。！？!?]+[、。！？!?]*[」』）)]*", text.replace(" ", "")):
            n = -(-len(piece) // JA_MAX)          # even split of over-long pieces
            size = -(-len(piece) // n)
            lines += [piece[i:i + size] for i in range(0, len(piece), size)]
        fixed = []
        for l in lines:
            m = re.match(r"^([」』）)、。！？]+)(.*)$", l)          # never start a line with a closing mark: move it to the previous line
            if m and fixed:
                fixed[-1] += m.group(1)
                l = m.group(2)
            if l:
                fixed.append(l)
        return [l.rstrip("。") or l for l in fixed]
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > EN_MAX:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
        if re.search(r"[.!?]$", w):
            lines.append(cur); cur = ""
    return lines + ([cur] if cur else [])


def _ts(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def make_srt(sections, durations, fps=30) -> str:
    """Each line gets time proportional to its character count within the section's narration span;
    section starts are offset by the cumulative (narration + 0.4 s pause) of earlier sections."""
    out, offset, n = [], 0.0, 0
    for sec, d in zip(sections, durations):
        lines = split_lines(sec["narration"])
        total = sum(len(l) for l in lines) or 1
        t = offset
        for l in lines:
            end = t + d * len(l) / total
            n += 1
            out.append(f"{n}\n{_ts(t)} --> {_ts(end)}\n{l}\n")
            t = end
        offset += span(d, fps)
    return "\n".join(out)


# ---------- assembly ----------
def _load(project_dir):
    sc = json.loads((project_dir / "script.json").read_text("utf-8"))
    sections = sc["sections"] if isinstance(sc, dict) else sc
    first = 0 if (project_dir / "voice" / "section_00.wav").exists() else 1
    names = [f"section_{i + first:02d}" for i in range(len(sections))]
    wavs = [project_dir / "voice" / f"{n}.wav" for n in names]
    pngs = [project_dir / "visuals" / f"{n}.png" for n in names]
    try:
        raw = json.loads((project_dir / "voice" / "durations.json").read_text())
        vals = raw if isinstance(raw, list) else [raw[n] if n in raw else raw[str(i + first)] for i, n in enumerate(names)]
        durs = [float(v) for v in vals]
        assert len(durs) == len(sections)
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        durs = [probe_duration(w) for w in wavs]
    return sections, wavs, pngs, durs


def _kenburns(i, frames, fps, size=(1920, 1080)):
    """Mode i%4: zoom in, zoom out, pan right, pan left (slow, over the clip). Source is upscaled 1.25x before zoompan."""
    m = i % 4
    z = ["1+0.12*on/%d" % frames, "1.12-0.12*on/%d" % frames, "1.1", "1.1"][m]
    if m == 2:
        x = "(iw-iw/zoom)*on/%d" % frames
    elif m == 3:
        x = "(iw-iw/zoom)*(1-on/%d)" % frames
    else:
        x = "iw/2-iw/zoom/2"
    w, h = size
    return (f"scale={w * 5 // 4}:{h * 5 // 4},zoompan=z='{z}':x='{x}':y='ih/2-ih/zoom/2':d={frames}:s={w}x{h}:fps={fps},format=yuv420p")


def find_beats(project_dir, name):
    """Sorted visuals/<name>_BB.png beat images (BB = digits) for a section name like 'section_01'."""
    pat = re.compile(rf"^{re.escape(name)}_(\d+)\.png$")
    return sorted((p for p in (Path(project_dir) / "visuals").glob(f"{name}_*.png") if pat.match(p.name)),
                  key=lambda p: int(pat.match(p.name).group(1)))


def _beat_weights(project_dir, name, beats):
    """chars per beat from storyboard.json; equal weights if file/entries are missing."""
    try:
        sec = int(name.split("_")[-1])
        sb = json.loads((Path(project_dir) / "storyboard.json").read_text("utf-8"))
        chars = {int(b["beat"]): float(b["chars"]) for b in sb["beats"] if int(b["section"]) == sec}
        w = [chars[int(re.search(r"_(\d+)\.png$", p.name).group(1))] for p in beats]
        if all(x > 0 for x in w):
            return w
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return [1.0] * len(beats)


def split_frames(total, weights):
    """Split total frames in proportion to weights; every beat gets >= 1 frame; sums exactly to total."""
    n, tw, acc, bounds = len(weights), float(sum(weights)), 0.0, []
    for k, w in enumerate(weights):
        acc += w
        b = total if k == n - 1 else round(acc / tw * total)
        b = max(b, (bounds[-1] if bounds else 0) + 1)
        bounds.append(min(b, total - (n - 1 - k)))
    return [b - a for a, b in zip([0] + bounds[:-1], bounds)]


def assemble(project_dir: Path, fps=30) -> Path:
    project_dir = Path(project_dir)
    sections, wavs, pngs, durs = _load(project_dir)
    final = project_dir / "final.mp4"
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps)]
    with tempfile.TemporaryDirectory(dir=project_dir) as tmp:
        tmp = Path(tmp)
        clips, k = [], 0                       # k: global image counter for Ken Burns alternation
        for i, (wav, png, d) in enumerate(zip(wavs, pngs, durs)):
            frames = round((d + PAUSE) * fps)
            clip = tmp / f"clip_{i:02d}.mp4"
            beats = find_beats(project_dir, png.stem)
            if len(beats) >= 2:
                counts = split_frames(frames, _beat_weights(project_dir, png.stem, beats))
                parts = []
                for j, (bp, n) in enumerate(zip(beats, counts)):
                    part = tmp / f"beat_{i:02d}_{j:02d}.mp4"
                    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-i", str(bp),
                          "-vf", _kenburns(k, n, fps), "-frames:v", str(n), *enc, "-an", str(part)])
                    parts.append(part)
                    k += 1
                plist = tmp / f"beats_{i:02d}.txt"
                plist.write_text("".join(f"file '{c}'\n" for c in parts))
                vid = tmp / f"vid_{i:02d}.mp4"
                _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(plist), "-c", "copy", str(vid)])
                _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                      "-c:v", "copy", "-af", "aresample=48000,apad", "-ac", "2",
                      "-t", f"{frames / fps:.4f}", "-c:a", "aac", "-b:a", "192k", str(clip)])
            else:
                src = png if png.exists() or not beats else beats[0]
                _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-i", str(src), "-i", str(wav),
                      "-vf", _kenburns(k, frames, fps), "-af", "aresample=48000,apad", "-ac", "2", "-frames:v", str(frames),
                      "-t", f"{frames / fps:.4f}", *enc, "-c:a", "aac", "-b:a", "192k", str(clip)])
                k += 1
            clips.append(clip)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        base = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "copy"]
        total = sum(round((d + PAUSE) * fps) for d in durs) / fps   # video length; trims AAC priming/padding overhang
        tail = ["-t", f"{total:.4f}", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)]
        try:
            _run(base + ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] + tail)
        except RuntimeError:   # loudnorm yields NaN on fully silent audio; keep the audio as is
            _run(base + tail)
    (project_dir / "final.srt").write_text(make_srt(sections, durs, fps), "utf-8")
    return final


# ---------- Shorts (1080x1920) ----------
def short_span(duration, fps=30) -> float:
    return round((duration + SHORT_PAUSE) * fps) / fps


def caption_groups(text, max_words=CAPTION_WORDS):
    """Word groups of 3-5 words (even sizes; a text of fewer than 3 words is one group)."""
    words = text.split()
    if not words:
        return []
    n = -(-len(words) // max_words)
    base, extra = divmod(len(words), n)
    out, i = [], 0
    for k in range(n):
        size = base + (1 if k < extra else 0)
        out.append(" ".join(words[i:i + size]))
        i += size
    return out


def make_caption_events(sections, durations, fps=30):
    """[(start, end, text)]: groups share the section's narration time in proportion to their characters;
    section starts are offset by the cumulative (narration + 0.2 s pause) of earlier sections."""
    events, offset = [], 0.0
    for sec, d in zip(sections, durations):
        groups = caption_groups(sec["narration"])
        total = sum(len(g) for g in groups) or 1
        t = offset
        for g in groups:
            end = t + d * len(g) / total
            events.append((t, end, g))
            t = end
        offset += short_span(d, fps)
    return events


def _ass_ts(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def short_font():
    """(font name, fonts dir): DejaVu Sans Bold if installed, else the IPAGothic fallback."""
    dj = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    return ("DejaVu Sans", str(dj.parent)) if dj.exists() else ("IPAGothic", FONTS_DIR)


def make_short_ass(events, font_name="DejaVu Sans", size=SHORT_SIZE, font_px=88):
    w, h = size
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font_name},{font_px},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,7,2,2,70,70,{h // 6},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [f"Dialogue: 0,{_ass_ts(a)},{_ass_ts(b)},Default,,0,0,0,,{t.replace(chr(10), ' ').replace('{', '(').replace('}', ')')}" for a, b, t in events]
    return head + "\n".join(lines) + "\n"


def assemble_short(project_dir: Path, fps=30) -> Path:
    """short.mp4: 1080x1920 H.264/AAC, one Ken Burns image per section, burned-in 3-5 word captions, loudness-normalized, <= 59 s."""
    project_dir = Path(project_dir)
    sections, wavs, pngs, durs = _load(project_dir)
    frames = [round((d + SHORT_PAUSE) * fps) for d in durs]
    total = sum(frames) / fps
    if total > SHORT_MAX:
        raise ValueError(f"short is {total:.1f} s long (voice {sum(durs):.1f} s + {SHORT_PAUSE} s pauses); the limit is {SHORT_MAX:.0f} s: shorten the script")
    out = project_dir / "short.mp4"
    font_name, fonts_dir = short_font()
    (project_dir / "short.ass").write_text(make_short_ass(make_caption_events(sections, durs, fps), font_name), "utf-8")
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps)]
    with tempfile.TemporaryDirectory(dir=project_dir) as tmp:
        tmp = Path(tmp)
        clips = []
        for i, (wav, png, n) in enumerate(zip(wavs, pngs, frames)):
            src = png if png.exists() else (find_beats(project_dir, png.stem) or [png])[0]
            clip = tmp / f"clip_{i:02d}.mp4"
            _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-i", str(src), "-i", str(wav),
                  "-vf", _kenburns(i, n, fps, SHORT_SIZE), "-af", "aresample=48000,apad", "-ac", "2", "-frames:v", str(n),
                  "-t", f"{n / fps:.4f}", *enc, "-c:a", "aac", "-b:a", "192k", str(clip)])
            clips.append(clip)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        base = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-vf", f"subtitles=short.ass:fontsdir={fonts_dir},format=yuv420p"]
        tail = ["-t", f"{total:.4f}", *enc, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out.resolve())]
        try:
            _run(base + ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] + tail, cwd=project_dir)
        except RuntimeError:   # loudnorm yields NaN on fully silent audio (mock voice); keep the audio as is
            _run(base + tail, cwd=project_dir)
    return out


def make_preview(project_dir, height=720, crf=28) -> Path:
    """Small review copy of final.mp4: H.264 + AAC 96k, given height, faststart."""
    project_dir = Path(project_dir)
    final = project_dir / "final.mp4"
    if not final.exists():
        raise FileNotFoundError("run assemble() first")
    out = project_dir / "preview.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-vf", f"scale=-2:{int(height)},format=yuv420p",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", str(int(crf)), "-r", "30",
          "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(out)])
    return out


def make_shorts(project_dir) -> Path:
    project_dir = Path(project_dir)
    final, srt = project_dir / "final.mp4", project_dir / "final.srt"
    if not final.exists() or not srt.exists():
        raise FileNotFoundError("run assemble() first")
    t = min(HOOK_MAX, probe_duration(final))
    # libass scales force_style units from its 384x288 default PlayRes: x6.67 on 1920 px -> FontSize 9 ~ 60 px, MarginV 57 ~ 380 px
    style = ("FontName=IPAGothic,FontSize=9,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=1.2,Shadow=0.5,Alignment=2,MarginV=57,MarginL=8,MarginR=8")
    fc = ("[0:v]split[a][b];"
          "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.15[bg];"
          "[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,"
          f"subtitles=final.srt:fontsdir={FONTS_DIR}:force_style='{style}',format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", "final.mp4", "-t", f"{t:.3f}", "-filter_complex", fc,
          "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", "30",
          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "shorts.mp4"], cwd=project_dir)
    return project_dir / "shorts.mp4"


# ---------- thumbnail ----------
def _wrap(draw, text, font, max_w):
    tokens = re.findall(r"[A-Za-z0-9'’\-]+|\s+|.", text)
    lines, cur = [], ""
    for tok in tokens:
        if cur and draw.textlength(cur + tok, font=font) > max_w and tok.strip():
            lines.append(cur.strip()); cur = tok.lstrip()
        else:
            cur += tok
    return lines + ([cur.strip()] if cur.strip() else [])


def thumbnail_text_from_title(title: str, max_chars: int = 16) -> str:
    """Fallback when the script has no `thumbnail_text`: the first segment of the title, trimmed at a natural break."""
    seg = re.split(r"[｜|]", title)[0].strip()
    if len(seg) <= max_chars:
        return seg
    cut = max(seg.rfind(c, 0, max_chars + 1) for c in "、， ,")
    return seg[:cut] if cut >= 6 else seg[:max_chars]


def make_thumbnail(project_dir, title: str, text: str = None) -> Path:
    """1280x720 thumbnail: a SHORT punchy line (<= 2 lines, large) at the bottom over a dark gradient so faces stay visible."""
    project_dir = Path(project_dir)
    vis = project_dir / "visuals"
    allp = sorted(vis.glob("section_*.png"))
    first = min(re.match(r"(section_\d+)", p.name).group(1) for p in allp)    # first section's stem
    cand = vis / f"{first}.png"
    src = cand if cand.exists() else (find_beats(project_dir, first) or allp)[0]   # else its first beat
    W, H = 1280, 720
    img = Image.open(src).convert("RGB")
    sc = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * sc), round(img.height * sc)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))
    grad = Image.linear_gradient("L").resize((W, H))           # 0 top -> 255 bottom
    img = Image.composite(Image.new("RGB", (W, H), "black"), img, grad.point(lambda v: 0 if v < 110 else int((v - 110) * 1.6)))
    draw, margin = ImageDraw.Draw(img), 60
    line = (text or thumbnail_text_from_title(title)).strip()
    for size in range(150, 49, -4):                            # largest size that fits in <= 2 lines within 90% of the width
        font = ImageFont.truetype(FONT, size)
        lines = _wrap(draw, line, font, int(W * 0.9) - margin)
        lh = int(size * 1.15)
        if len(lines) <= 2:
            break
    stroke = max(4, size // 9)
    y = H - margin - len(lines) * lh
    for l in lines:
        draw.text((margin, y), l, font=font, fill="#FFE600", stroke_width=stroke, stroke_fill="black")
        y += lh
    out = project_dir / "thumbnail.png"
    img.save(out)
    return out
