"""Make listening samples of several calm adult male VOICEVOX voices so the owner can pick one.

Run: python -m studio.voice_pick   (needs a running VOICEVOX engine and ffmpeg)
Env: PICK_TEXT overrides the sample text. Output: studio/work/voice_samples/
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import voice

# Names matched against the live /speakers list; missing ones are skipped.
CANDIDATE_NAMES = ["青山龍星", "玄野武宏", "白上虎太郎", "雀松朱司", "麒ヶ島宗麟",
                   "剣崎雌雄", "後鬼", "No.7", "黒沢冴白", "離途"]

DEFAULT_TEXT = ("お相手の話に、ゆっくりと耳を傾けてみましょう。"
                "言葉の合間にある小さな間や笑顔が、二人の距離を少しずつ近づけてくれます。")

OUT_DIR = Path(__file__).resolve().parent.parent / "work" / "voice_samples"
STYLE_PREFERRED = "ノーマル"


def pick_candidates(speakers_json, names=CANDIDATE_NAMES, max_styles=2):
    by_name = {sp.get("name"): sp for sp in speakers_json}
    out = []
    for name in names:
        sp = by_name.get(name)
        if not sp:
            continue
        styles = [s for s in sp.get("styles", []) if "id" in s]
        styles.sort(key=lambda s: s.get("name") != STYLE_PREFERRED)  # stable: ノーマル first
        for st in styles[:max_styles]:
            out.append({"speaker": name, "style": st.get("name"), "id": st["id"]})
    return out


def slug(s):
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(s)).strip("_.")
    return s or "x"


def sample_filename(index, speaker, style):
    return f"{index:02d}_{slug(speaker)}_{slug(style)}.mp3"


def _to_mp3(wav, mp3):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-ac", "1", "-b:a", "64k", str(mp3)],
                   check=True, capture_output=True, text=True)


def build_samples(candidates, text, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, failures = [], []
    for i, c in enumerate(candidates, 1):
        fname = sample_filename(i, c["speaker"], c["style"])
        wav = out_dir / f"_tmp_{i:02d}.wav"
        try:
            v = voice.VoicevoxVoice(speaker=c["id"], timeout=120)
            v.synthesize(text, "ja", wav)
            _to_mp3(wav, out_dir / fname)
            seconds = voice.probe_duration(out_dir / fname)
        except Exception as e:  # keep going on a per-speaker failure
            failures.append({"speaker": c["speaker"], "style": c["style"], "id": c["id"],
                             "error": f"{type(e).__name__}: {e}"})
            print(f"FAIL {c['speaker']} ({c['style']}, id {c['id']}): {type(e).__name__}: {e}", file=sys.stderr)
            continue
        finally:
            wav.unlink(missing_ok=True)
        entries.append({"speaker": c["speaker"], "style": c["style"], "id": c["id"], "file": fname,
                        "seconds": seconds, "credit": f"VOICEVOX:{c['speaker']}"})
        print(f"{fname}\t{c['speaker']}\t{c['style']}\tid={c['id']}\t{seconds:.1f}s\tVOICEVOX:{c['speaker']}")
    (out_dir / "candidates.json").write_text(
        json.dumps({"text": text, "samples": entries, "failures": failures}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return entries, failures


def main():
    import requests
    text = os.environ.get("PICK_TEXT") or DEFAULT_TEXT
    v = voice.VoicevoxVoice(timeout=120)
    try:
        speakers = v.session.get(v.base_url + "/speakers", timeout=30).json()
    except requests.RequestException as e:
        print(f"FAIL: cannot read /speakers from {v.base_url}: {e}", file=sys.stderr)
        return 1
    candidates = pick_candidates(speakers)
    missing = [n for n in CANDIDATE_NAMES if n not in {c["speaker"] for c in candidates}]
    if missing:
        print(f"not in engine speakers: {', '.join(missing)}")
    entries, failures = build_samples(candidates, text, OUT_DIR)
    print(f"samples: {len(entries)} ok, {len(failures)} failed")
    return 0 if entries else 1


if __name__ == "__main__":
    sys.exit(main())
