"""Ground-truth evaluation of video understanding (directive 5-2 / 10). Pure scoring functions + defect builders (ffmpeg) + a Files-API uploader.
The point: a model that returns fluent text is NOT yet shown to see/hear the video. We measure it against facts we control:
  * transcript accuracy vs the exact subtitle text of our own video (character error rate),
  * scene-cut timestamps vs FFmpeg's objective scene detection (precision / recall within a tolerance),
  * injected defects (muted window, shuffled segments, black-out, audio shifted) -> detection rate and false-alarm count,
  * cost and time per analysis."""
import json
import re
import subprocess
import time
from pathlib import Path

import requests

from . import gemini


# ---------- scoring (pure) ----------
def _norm(s):
    return re.sub(r"[\s、。,.!?！？「」『』()（）\-ー]", "", s or "")


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(reference, hypothesis):
    """Character error rate after removing spaces/punctuation. 0 = perfect; can exceed 1."""
    r, h = _norm(reference), _norm(hypothesis)
    return edit_distance(r, h) / max(1, len(r))


def mmss(t):
    """'MM:SS' / 'HH:MM:SS' / seconds -> float seconds."""
    if isinstance(t, (int, float)):
        return float(t)
    p = [float(x) for x in str(t).strip().split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def match_events(truth, reported, tol=2.0):
    """Greedy one-to-one matching of event times. Returns dict(precision, recall, f1, tp, fp, fn, mean_abs_error)."""
    truth, reported = sorted(truth), sorted(reported)
    used, errs = set(), []
    for t in truth:
        best = None
        for i, r in enumerate(reported):
            if i not in used and abs(r - t) <= tol and (best is None or abs(r - t) < abs(reported[best] - t)):
                best = i
        if best is not None:
            used.add(best)
            errs.append(abs(reported[best] - t))
    tp = len(used)
    fp, fn = len(reported) - tp, len(truth) - tp
    p = tp / max(1, tp + fp)
    r = tp / max(1, tp + fn)
    return dict(precision=round(p, 3), recall=round(r, 3), f1=round(2 * p * r / max(1e-9, p + r), 3), tp=tp, fp=fp, fn=fn,
                mean_abs_error=round(sum(errs) / len(errs), 2) if errs else None)


def defect_detection(injected, reported_times, tol=10.0):
    """injected: [{'type','start','end'}]; reported_times: seconds where the model claims an anomaly. A defect counts as detected if any report falls
    within [start-tol, end+tol]. Reports matching no defect are false alarms."""
    detected, hit = [], set()
    for d in injected:
        ok = [i for i, t in enumerate(reported_times) if d["start"] - tol <= t <= d["end"] + tol]
        hit.update(ok)
        detected.append(dict(type=d["type"], detected=bool(ok)))
    return dict(detected=detected, detection_rate=round(sum(x["detected"] for x in detected) / max(1, len(injected)), 3), false_alarms=len(reported_times) - len(hit))


def srt_window_text(srt_text, start, end):
    """Concatenate subtitle lines whose time range overlaps [start, end] seconds."""
    out = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = block.splitlines()
        m = next((re.match(r"(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)", ln) for ln in lines if "-->" in ln), None)
        if not m:
            continue
        a = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        b = int(m[5]) * 3600 + int(m[6]) * 60 + int(m[7]) + int(m[8]) / 1000
        if b >= start and a <= end:
            out.append("".join(ln for ln in lines if "-->" not in ln and not ln.strip().isdigit()))
    return "".join(out)


# ---------- objective measurements / defect builders (ffmpeg) ----------
def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def ffmpeg_scene_cuts(path, threshold=0.3):
    """Scene-cut times (s) by FFmpeg's scene score: the objective reference for '场面転換'."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [float(m.group(1)) for m in re.finditer(r"pts_time:([0-9.]+)", p.stderr)]


def build_defects(src, outdir, duration):
    """Make one defective copy per defect type; returns [(path, injected_defects_list)]. Positions are fractions of the duration (deterministic)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    s1, s2, s3 = duration * 0.25, duration * 0.5, duration * 0.75
    made = []
    p = outdir / "defect_mute.mp4"                              # audio removed for 20 s
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", f"volume=enable='between(t,{s1:.1f},{s1 + 20:.1f})':volume=0", "-c:v", "copy", str(p)])
    made.append((p, [dict(type="audio_dropout", start=s1, end=s1 + 20)]))
    p = outdir / "defect_blackout.mp4"                          # picture black for 8 s
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", f"drawbox=enable='between(t,{s2:.1f},{s2 + 8:.1f})':x=0:y=0:w=iw:h=ih:color=black:t=fill", "-c:a", "copy", str(p)])
    made.append((p, [dict(type="video_blackout", start=s2, end=s2 + 8)]))
    p = outdir / "defect_av_shift.mp4"                          # audio delayed 4 s for the whole video (desync)
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-itsoffset", "4", "-i", str(src), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", str(p)])
    made.append((p, [dict(type="av_desync_4s", start=0, end=duration)]))
    return made


# ---------- Files API upload ----------
def upload_file(path, display_name=None, mime="video/mp4", timeout=600):
    path = Path(path)
    size = path.stat().st_size
    key = gemini.api_key()
    r = requests.post("https://generativelanguage.googleapis.com/upload/v1beta/files",
                      headers={"x-goog-api-key": key, "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                               "X-Goog-Upload-Header-Content-Length": str(size), "X-Goog-Upload-Header-Content-Type": mime, "Content-Type": "application/json"},
                      json={"file": {"display_name": display_name or path.name}}, timeout=60)
    r.raise_for_status()
    url = r.headers["X-Goog-Upload-URL"]
    with open(path, "rb") as f:
        r2 = requests.post(url, headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"}, data=f, timeout=timeout)
    r2.raise_for_status()
    info = r2.json()["file"]
    t0 = time.time()
    while info.get("state") == "PROCESSING" and time.time() - t0 < 300:
        time.sleep(5)
        info = requests.get(f"https://generativelanguage.googleapis.com/v1beta/{info['name']}", headers={"x-goog-api-key": key}, timeout=30).json()
    if info.get("state") != "ACTIVE":
        raise RuntimeError(f"file not active: {info.get('state')}")
    return info["uri"], info["name"]


def delete_file(name):
    requests.delete(f"https://generativelanguage.googleapis.com/v1beta/{name}", headers={"x-goog-api-key": gemini.api_key()}, timeout=30)
