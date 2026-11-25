"""Watch real YouTube Shorts (picture + sound, public URL input) and describe what they actually do. View counts are NOT given to the model (no bias); they are joined afterwards.
Usage: python -m studio.vu_shorts <id1,id2,...> [model]. Output: work/gemini_live/marketing/shorts/<id>.md ; spend capped."""
import json
import sys

from . import vu_diag as d
from .vu_batch import gen_retry
from .vu_marketing import RULES

PROMPT = RULES + ("課題: これは縦型の短い動画(YouTubeショート)です。次の項目で、簡潔に分析してください(全体で1,200字程度)。\n"
                  "1) 実際の長さ(秒)。\n"
                  "2) 冒頭0〜3秒に、映像で何が起き、音声で何と言っているか(短く引用)。\n"
                  "3) 秒ごとの構成(区切りごとに、映像・音声・文字の内容)。\n"
                  "4) 画面の文字(字幕・テロップ)の出し方、声(ナレーションの有無・話し方・速さ)、BGM・効果音。\n"
                  "5) 終わり方(ループ、オチ、行動の呼びかけ、またはなし)。\n"
                  "6) 映像の出どころ: 制作者が自作したか、テレビ・アニメ・他者の動画の切り抜き/転載か、ストック素材か、AI生成か。見て判断できる根拠も書く。判断できなければ「不明」。\n"
                  "7) 最後まで見たくなる仕掛け(観察できるもの)。\n"
                  "8) 同じ型を、一人の制作者がAIと既存素材だけで作るとしたら、材料と難しさ(観察できる範囲で。推測は推測と書く)。")


def main():
    ids = [x for x in sys.argv[1].split(",") if x]
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-3.8-flash"
    out = d.OUT.parent / "marketing" / "shorts"
    out.mkdir(parents=True, exist_ok=True)
    for vid in ids:
        if d.SPENT[0] > 1.0:
            print("BUDGET CAP"); break
        r = gen_retry(model, f"https://www.youtube.com/watch?v={vid}", PROMPT, f"{model}|{vid}|short")
        (out / f"{vid}.md").write_text(r["text"] or f"(failed: HTTP {r['http_status']})", encoding="utf-8")
        print(f"SHORT {vid} http={r['http_status']} finish={r['finishReason']} usage={r['usage']} cost={r['cost_usd']} chars={len(r['text'])}", flush=True)
    (out / "raw_log.json").write_text(json.dumps(d.LOG, ensure_ascii=False), encoding="utf-8")
    print("TOTAL cost_usd", round(d.SPENT[0], 4))


if __name__ == "__main__":
    main()
