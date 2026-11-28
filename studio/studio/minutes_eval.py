"""Technical verification of 'meeting minutes' (transcript + summary) with Gemini, against a KNOWN script (needs GEMINI_API_KEY; run in Actions).
Ground truth: a synthetic 3-person real-estate meeting (specialist terms, amounts, dates, names) is spoken by Gemini TTS (3 voices), then degraded (clean / noisy / phone band).
Measured per condition: character error rate of the transcript, recall of key terms / numbers / dates / names, speaker-label count, and for the generated minutes:
decision recall, action-item recall (owner + due date), and unsupported numbers/dates (hallucination check). LIMITS: synthetic speech is cleaner than real meetings; one run per condition; AI-vs-script checks are mechanical (no LLM judge).
Usage: python -m studio.minutes_eval        Output: work/gemini_live/minutes_eval.json (+ transcripts, minutes)"""
import base64
import io
import json
import random
import re
import struct
import sys
import time
import unicodedata
import wave
from pathlib import Path

from . import gemini

TTS_MODELS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview"]
ASR_MODEL = "gemini-3.8-flash"
VOICES = {"田中": "Charon", "佐藤": "Kore", "鈴木": "Iapetus"}
STYLE = "Speak naturally in Japanese at a normal pace, like a business meeting with colleagues. Clear and calm."
SCRIPT = [
    ("田中", "それでは、本日の議題は中古マンションの売買契約についてです。物件価格は売主と調整して、4,800万円で合意する方向でよろしいでしょうか。"),
    ("佐藤", "はい、4,800万円で問題ありません。媒介契約は専任媒介で、期間は3か月になっています。"),
    ("鈴木", "手付金は150万円、契約日は12月18日で先方の了承をいただいています。"),
    ("田中", "引き渡しは1月31日でお願いします。固定資産税の精算は、引き渡し日を基準に日割りで行います。"),
    ("佐藤", "仲介手数料は、物件価格の3パーセントに6万円を加えた額で、消費税は別になります。"),
    ("鈴木", "この物件は建ぺい率が60パーセント、容積率が200パーセントです。境界確認書は売主から受け取り済みです。"),
    ("田中", "契約不適合責任の期間は、引き渡しから2年でよろしいですか。"),
    ("佐藤", "はい、売主様も2年で了承されています。"),
    ("田中", "では、重要事項説明書の作成は佐藤さん、12月10日までにお願いします。"),
    ("佐藤", "承知しました。12月10日までに作成します。"),
    ("田中", "鈴木さんは、買主様の住宅ローン事前審査の結果を、12月12日までに確認してください。"),
    ("鈴木", "わかりました。みずほ銀行の結果を12月12日までに確認して、共有します。"),
    ("田中", "私は、売主様へ最終条件を12月15日までに送ります。ほかに確認事項はありますか。"),
    ("鈴木", "一点、インスペクションを実施するかどうかは、まだ決まっていません。買主様の意向を確認します。"),
    ("田中", "では、その件は未決事項として残しましょう。以上で終わります。ありがとうございました。"),
]
KEY_TERMS = ["媒介契約", "専任媒介", "手付金", "固定資産税", "仲介手数料", "建ぺい率", "容積率", "境界確認書", "契約不適合責任", "重要事項説明書", "住宅ローン事前審査", "インスペクション"]
# facts: (label, [accepted surface forms after normalisation])
FACTS = [("価格4800万", ["4800万円", "四千八百万円"]), ("手付金150万", ["150万円", "百五十万円"]), ("契約日12/18", ["12月18日", "十二月十八日"]), ("引渡1/31", ["1月31日", "一月三十一日"]),
         ("手数料3%", ["3パーセント", "3%", "三パーセント"]), ("手数料6万", ["6万円", "六万円"]), ("建ぺい率60", ["60パーセント", "60%", "六十パーセント"]), ("容積率200", ["200パーセント", "200%", "二百パーセント"]),
         ("責任2年", ["2年", "二年"]), ("書類12/10", ["12月10日", "十二月十日"]), ("審査12/12", ["12月12日", "十二月十二日"]), ("最終条件12/15", ["12月15日", "十二月十五日"]),
         ("専任3か月", ["3か月", "3ヶ月", "3カ月", "三か月", "三ヶ月"]), ("銀行名", ["みずほ銀行"])]
DECISIONS = [("価格", ["4800万円", "四千八百万円"]), ("手付金", ["150万円"]), ("契約日", ["12月18日"]), ("引渡", ["1月31日"]), ("仲介手数料", ["3パーセント", "3%"])]
ACTIONS = [("佐藤", ["12月10日"]), ("鈴木", ["12月12日"]), ("田中", ["12月15日"])]


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace(",", "").replace("，", "")
    return re.sub(r"[\s、。,.!?！？「」『』()（）・:：\-ー〜~*#]", "", s)


def cer(ref, hyp):
    a, b = norm(ref), norm(hyp)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(a))


def recall(items, text):
    t = norm(text)
    hit = [lab for lab, forms in items if any(norm(f) in t for f in forms)]
    return len(hit), len(items), [lab for lab, _ in items if lab not in hit]


def tts_all():
    pcm, rate = b"", 24000
    for sp, line in SCRIPT:
        for model in TTS_MODELS:
            try:
                data, rate, _ = gemini.tts(model, line, VOICES[sp], STYLE)
                break
            except Exception as e:  # noqa: BLE001
                print("TTS retry", model, type(e).__name__, str(e)[:100], flush=True)
                time.sleep(3)
        else:
            raise RuntimeError("TTS failed for all models")
        pcm += data + b"\x00\x00" * int(rate * 0.5)
    return pcm, rate


def wav_bytes(pcm, rate):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return b.getvalue()


def degrade(pcm, rate, kind):
    n = len(pcm) // 2
    s = list(struct.unpack("<%dh" % n, pcm[: n * 2]))
    rng = random.Random(20261128)
    if kind == "noisy":   # room noise at roughly 15 dB below the speech peak level
        peak = max(abs(x) for x in s) or 1
        amp = peak * 0.12
        s = [max(-32768, min(32767, int(x + rng.gauss(0, amp)))) for x in s]
    elif kind == "phone":   # crude 8 kHz band: average 3 samples (24k -> 8k), light noise
        m = len(s) // 3
        s = [int(sum(s[3 * i: 3 * i + 3]) / 3 + rng.gauss(0, 150)) for i in range(m)]
        rate = rate // 3
    return struct.pack("<%dh" % len(s), *[max(-32768, min(32767, x)) for x in s]), rate


def ask(prompt, audio_wav=None):
    parts = [{"text": prompt}]
    if audio_wav:
        parts.append({"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(audio_wav).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingBudget": 0}}}
    try:
        resp = gemini.generate_content(ASR_MODEL, body)
    except gemini.GeminiError:
        body["generationConfig"].pop("thinkingConfig", None)
        resp = gemini.generate_content(ASR_MODEL, body)
    return gemini.text_of(resp), gemini.usage(resp)


ASR_PROMPT = "この会議の音声を、正確に文字起こししてください。話者が変わるごとに行を分け、行頭に話者ラベル(話者A、話者B、話者C)を付けてください。句読点を付け、専門用語・金額・日付・固有名詞は聞こえたとおり正確に書いてください。要約や注釈は付けないでください。"
MIN_PROMPT = """次の会議の文字起こしから、議事録をJSONだけで作ってください。文字起こしに書かれていないことは書かないでください。
{"summary": ["要点を最大5行"], "decisions": ["決定事項(金額・日付を含める)"], "actions": [{"owner": "担当者名", "task": "内容", "due": "期限"}], "open_issues": ["未決事項"]}
文字起こし:
"""


def number_like(text):
    t = unicodedata.normalize("NFKC", text).replace(",", "")
    return set(re.findall(r"\d+(?:月\d+日|万円|%|パーセント|年|か月|ヶ月)?", t))


def main():
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    ref = "".join(line for _, line in SCRIPT)
    pcm, rate = tts_all()
    print("TTS ok, seconds:", round(len(pcm) / 2 / rate, 1), flush=True)
    results, usage = {}, {"in": 0, "out": 0}
    for kind in ("clean", "noisy", "phone"):
        d_pcm, d_rate = degrade(pcm, rate, kind) if kind != "clean" else (pcm, rate)
        wav = wav_bytes(d_pcm, d_rate)
        hyp, u = ask(ASR_PROMPT, wav)
        usage["in"] += u["input_tokens"]; usage["out"] += u["output_tokens"] + u["thought_tokens"]
        labels = set(re.findall(r"^(話者[A-Z])", hyp, re.M))
        tr_clean = re.sub(r"^話者[A-Z][::]?\s*", "", hyp, flags=re.M)
        kt = recall([(t, [t]) for t in KEY_TERMS], tr_clean)
        fc = recall(FACTS, tr_clean)
        mins_txt, u2 = ask(MIN_PROMPT + tr_clean)
        usage["in"] += u2["input_tokens"]; usage["out"] += u2["output_tokens"] + u2["thought_tokens"]
        m = re.search(r"\{.*\}", mins_txt, re.S)
        try:
            mins = json.loads(m.group(0)) if m else {}
        except ValueError:
            mins = {}
        dec_txt = " ".join(mins.get("decisions", [])) + " " + " ".join(mins.get("summary", []))
        dr = recall(DECISIONS, dec_txt)
        act_ok = 0
        for who, dues in ACTIONS:
            if any(a.get("owner") and who in a["owner"] and any(norm(x) in norm(str(a.get("due", "")) + str(a.get("task", ""))) for x in dues) for a in mins.get("actions", [])):
                act_ok += 1
        unsupported = sorted(number_like(json.dumps(mins, ensure_ascii=False)) - number_like(ref))
        results[kind] = dict(cer=round(cer(ref, tr_clean), 4), key_terms=f"{kt[0]}/{kt[1]}", key_terms_missing=kt[2], facts=f"{fc[0]}/{fc[1]}", facts_missing=fc[2], speaker_labels=len(labels),
                             minutes_decisions=f"{dr[0]}/{dr[1]}", minutes_decisions_missing=dr[2], minutes_actions=f"{act_ok}/{len(ACTIONS)}", unsupported_numbers=unsupported,
                             open_issue_mentions_inspection=any("インスペクション" in x for x in mins.get("open_issues", [])), minutes_ok=bool(mins))
        (out / f"minutes_{kind}_transcript.txt").write_text(hyp, "utf-8")
        (out / f"minutes_{kind}_minutes.json").write_text(json.dumps(mins, ensure_ascii=False, indent=1), "utf-8")
        print(kind, json.dumps(results[kind], ensure_ascii=False), flush=True)
    (out / "minutes_eval.json").write_text(json.dumps(dict(results=results, usage=usage, model=ASR_MODEL, tts=TTS_MODELS[0], audio_seconds=round(len(pcm) / 2 / rate, 1)), ensure_ascii=False, indent=1), "utf-8")
    print("USAGE", usage, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
