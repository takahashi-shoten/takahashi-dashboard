"""Diagnosis of why video+audio understanding failed in run #51. Minimal prompts, RAW responses saved, no parsing that can turn failure into success.
Inputs from our own E1 clip: A = mp4 with audio, B = same without audio, C = wav only (no picture, so no burned-in subtitles), plus defect copies.
Usage: python -m studio.vu_diag <video.mp4> <subtitles.srt> [models comma-separated] [start_s] [dur_s]"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import gemini, video_analysis as va, vu_eval as ev

P_AUDIO = ("この動画（音声）から実際に聞き取れる日本語の発言を書き起こしてください。字幕を読み取った内容と、音声から聞き取った内容を区別してください。"
           "音声を認識できない場合は、そのことを明記してください。")
P_VIDEO = ("この動画に映っている内容を、開始から終了まで時間順に説明してください。実際に映像から確認できたものだけを記述し、重要な画面変化には時間位置を付けてください。")
P_SILENT = ("発話がない区間や、音声全体が無音になる区間があれば、その開始時刻と終了時刻（秒）を報告してください。無ければ「なし」と答えてください。")
P_BLACK = ("画面全体が黒くなる区間が存在するか確認してください。存在する場合は開始時刻、終了時刻、継続時間（秒）を報告してください。無ければ「なし」と答えてください。")
BASE = "https://generativelanguage.googleapis.com/v1beta/"
OUT = Path(__file__).resolve().parent.parent / "work" / "gemini_live" / "diag"
LOG = []
SPENT = [0.0]
CAP_USD = 4.0


def sh(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def upload(path, mime):
    return ev.upload_file(path, mime=mime)  # waits until state == ACTIVE (raises otherwise)


def list_models():
    names, tok = [], None
    while True:
        r = requests.get(BASE + "models", params={"pageSize": 200, **({"pageToken": tok} if tok else {})}, headers={"x-goog-api-key": gemini.api_key()}, timeout=60).json()
        names += [(m["name"].split("/")[-1], m.get("supportedGenerationMethods", [])) for m in r.get("models", [])]
        tok = r.get("nextPageToken")
        if not tok:
            return names


def count_tokens(model, uri, mime, label):
    body = {"contents": [{"parts": [{"fileData": {"fileUri": uri, "mimeType": mime}}]}]}
    r = requests.post(f"{BASE}models/{model}:countTokens", json=body, headers={"x-goog-api-key": gemini.api_key()}, timeout=120)
    rec = dict(kind="countTokens", label=label, model=model, status=r.status_code, raw=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:500], at=now())
    LOG.append(rec)
    print(f"COUNT {label} {model} status={r.status_code} -> {json.dumps(rec['raw'], ensure_ascii=False)[:300]}", flush=True)
    return rec


def gen(model, uri, mime, prompt, label, resolution=None):
    part = {"fileData": {"fileUri": uri, "mimeType": mime}}
    body = {"contents": [{"parts": [part, {"text": prompt}]}], "generationConfig": {"maxOutputTokens": 8192}}
    if resolution:
        body["generationConfig"]["mediaResolution"] = resolution
    t = time.time()
    r = requests.post(f"{BASE}models/{model}:generateContent", json=body, headers={"x-goog-api-key": gemini.api_key(), "Content-Type": "application/json"}, timeout=600)
    sec = round(time.time() - t, 1)
    try:
        raw = r.json()
    except ValueError:
        raw = {"non_json": r.text[:800]}
    u = va.usage_summary(raw) if r.status_code == 200 else {}
    cost = None
    try:
        cost = va.estimate_cost(model, u) if u else None
    except Exception:
        cost = None
    SPENT[0] += cost or 0
    cand = (raw.get("candidates") or [{}])[0] if isinstance(raw, dict) else {}
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) if "text" in p and not p.get("thought"))
    rec = dict(kind="generate", label=label, model=model, at=now(), seconds=sec, http_status=r.status_code, request=dict(prompt=prompt, mime=mime, uri=uri, resolution=resolution, maxOutputTokens=8192),
               finishReason=cand.get("finishReason"), promptFeedback=raw.get("promptFeedback") if isinstance(raw, dict) else None, usage=u, cost_usd=cost, modelVersion=raw.get("modelVersion") if isinstance(raw, dict) else None,
               text=text, raw=raw)
    LOG.append(rec)
    print(f"GEN {label} {model} http={r.status_code} finish={rec['finishReason']} sec={sec} usage={u} cost={cost} chars={len(text)} spent={round(SPENT[0], 4)}\n  TEXT: {text[:400]!r}", flush=True)
    return rec


def times_in(text):
    out = []
    for m in re.finditer(r"(\d{1,2}):(\d{2})|(\d+(?:\.\d+)?)\s*秒", text):
        out.append(int(m[1]) * 60 + int(m[2]) if m[1] else float(m[3]))
    return out


def main():
    src, srt = Path(sys.argv[1]), Path(sys.argv[2])
    want = [m for m in (sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3].strip() else []) if m]
    start = float(sys.argv[4]) if len(sys.argv) > 4 else 120.0
    dur = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
    OUT.mkdir(parents=True, exist_ok=True)
    A, B, C = OUT / "A_audio.mp4", OUT / "B_noaudio.mp4", OUT / "C_audio.wav"
    sh(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", str(A)])
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(A), "-an", "-c:v", "copy", str(B)])
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(A), "-vn", "-ac", "1", "-ar", "16000", str(C)])
    vol = subprocess.run(["ffmpeg", "-i", str(A), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    print("A volume:", re.findall(r"(mean_volume|max_volume): ([-0-9.]+) dB", vol))
    probe = sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,sample_rate,channels,duration", "-of", "json", str(A)]).stdout
    print("A probe:", probe.replace("\n", " "))
    defects = {p.name: inj for p, inj in ev.build_defects(A, OUT / "defects", dur)}
    mute, black = OUT / "defects" / "defect_mute.mp4", OUT / "defects" / "defect_blackout.mp4"
    ref = ev.srt_window_text(srt.read_text(encoding="utf-8"), start + 1, start + dur - 1)
    print("REF chars", len(ev._norm(ref)), "REF head:", ref[:120])
    names = list_models()
    gm = sorted(n for n, m in names if "generateContent" in m and n.startswith("gemini-") and not re.search(r"image|tts|live|audio|embedding|robotics|computer|thinking-exp|customtools|learnlm|gemma", n))
    print("AVAILABLE gemini generateContent models:", gm)
    models = want or [m for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"] if m in gm]
    pros = [n for n in gm if re.search(r"-pro", n) and "preview" not in n] or [n for n in gm if re.search(r"-pro", n)]
    if not want and pros:
        models.append(pros[-1])
    print("MODELS TO TEST:", models)
    uris = {}
    for key, path, mime in [("A", A, "video/mp4"), ("B", B, "video/mp4"), ("C", C, "audio/wav"), ("MUTE", mute, "video/mp4"), ("BLACK", black, "video/mp4")]:
        uris[key] = (upload(path, mime)[0], mime)
        print("UPLOADED", key, path.name, path.stat().st_size, "bytes", mime)
    first = models[0]
    for key in ("A", "B", "C"):
        count_tokens(first, *uris[key], label=f"count_{key}")
    results = {}
    for mi, model in enumerate(models):
        if SPENT[0] > CAP_USD:
            print("BUDGET CAP reached"); break
        try:
            runs = [("A_audio", "A", P_AUDIO), ("C_audio", "C", P_AUDIO), ("A_video", "A", P_VIDEO), ("MUTE_silent", "MUTE", P_SILENT), ("A_silent_clean", "A", P_SILENT),
                    ("BLACK_black", "BLACK", P_BLACK), ("A_black_clean", "A", P_BLACK)]
            if mi == 0:
                runs.insert(2, ("B_audio", "B", P_AUDIO))
            for label, key, prompt in runs:
                uri, mime = uris[key]
                results[(model, label)] = gen(model, uri, mime, prompt, f"{model}|{label}")
        except Exception as e:
            print("MODEL FAILED", model, str(e)[:300])
            LOG.append(dict(kind="error", model=model, error=str(e)[:500], at=now()))
    # scoring (simple, transparent; raw texts are kept for manual review)
    summary = []
    mute_w, black_w = defects["defect_mute.mp4"][0], defects["defect_blackout.mp4"][0]
    for model in models:
        row = dict(model=model)
        for label in ("A_audio", "C_audio", "B_audio"):
            r = results.get((model, label))
            if r:
                row[f"cer_{label}"] = round(ev.cer(ref, r["text"]), 3) if r["text"] else None
                row[f"chars_{label}"] = len(ev._norm(r["text"]))
                row[f"audio_tokens_{label}"] = (r["usage"].get("by_modality") or {}).get("AUDIO")
                row[f"video_tokens_{label}"] = (r["usage"].get("by_modality") or {}).get("VIDEO")
        for label, w, tol in (("MUTE_silent", mute_w, 3.0), ("BLACK_black", black_w, 3.0)):
            r = results.get((model, label))
            if r:
                ts = times_in(r["text"])
                row[label + "_times"] = ts
                row[label + "_hit"] = any(w["start"] - tol <= t <= w["end"] + tol for t in ts)
        for label in ("A_silent_clean", "A_black_clean"):
            r = results.get((model, label))
            if r:
                row[label + "_reported_times"] = times_in(r["text"])
        summary.append(row)
    for s in summary:
        print("SUMMARY", json.dumps(s, ensure_ascii=False))
    (OUT / "vu_diag_raw.json").write_text(json.dumps(dict(ran_at=now(), clip=dict(start=start, dur=dur), ref_chars=len(ev._norm(ref)), defects=defects, summary=summary, log=LOG), ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOTAL cost_usd", round(SPENT[0], 4))


if __name__ == "__main__":
    main()
