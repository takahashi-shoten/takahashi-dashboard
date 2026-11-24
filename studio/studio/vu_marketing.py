"""Independent marketing analysis of a public YouTube video from its ACTUAL picture and sound (YouTube URL input = officially supported).
The owner's own human analysis is deliberately NOT given to the model (it is compared afterwards, outside this script).
Usage: python -m studio.vu_marketing <video_id> [model]   (needs GEMINI_API_KEY, YOUTUBE_API_KEY)
Saves: metadata, comments, 4 raw passes (+ usage/cost) under work/gemini_live/marketing/<id>/ . Spend is capped."""
import json
import os
import sys
from pathlib import Path

import requests

from . import vu_diag as d

RULES = ("あなたは動画マーケティングの分析者です。この動画の実際の映像と音声を見聞きして分析します（タイトルや概要欄だけに頼らない）。\n"
         "ルール: (1)『観察された事実』（時刻MM:SS付き。発言の引用は短く）と『解釈』を必ず分けて書く。 (2)見聞きできないこと（収益、視聴維持率、制作方法、視聴者の実際の反応）は「未確認」と書く。 "
         "(3)キャラクター（加工されたぬいぐるみ等）の動きと、話者本人の身体表現を混同しない。 (4)推測で補わない。根拠の時刻を付ける。 (5)日本語で、見出し付きの文章で書く。\n\n")

PASSES = {
    "p1_structure": RULES + ("課題: 構成と視聴者心理の時系列。\n"
                              "1) 冒頭0〜10秒に実際に話されている内容（短く引用）と、その狙いの解釈。\n"
                              "2) 動画全体の章立て（開始時刻・内容・役割）。動画の最後の時刻も書く。\n"
                              "3) 視聴者の心理がどう動くかの時系列（段階ごとに、根拠となる発言・映像の時刻を付ける）。\n"
                              "4) 視聴維持の仕掛け（予告、問いかけ、緩急、繰り返しなど）。\n"
                              "5) 行動の呼びかけ（登録・高評価・外部誘導・商品）の有無と時刻。無ければ「確認できない」。"),
    "p2_four_values": RULES + ("課題: 4種類の価値の分析。それぞれ『観察された事実（時刻付き）』『解釈』『効いていると考える理由』『反証・弱点』の順で書く。\n"
                                "A 情報的価値: 何を知ることができるか。当たり前の情報なのに聞きたくなる理由。比喩・経験談・具体例・根拠の使い方。\n"
                                "B 実用的価値: 視聴者が実際にできること。大きな目標を小さな行動に変える方法。時間・労力・費用・心理的障壁の下げ方。\n"
                                "C 感情的価値: 視聴者が求めている感情（共感・納得・安心・希望・危機感）。悩みや欲求の言語化。否定的感情から肯定的感情への転換。信頼感・親近感・愛着。視聴そのものが精神的報酬になるか。\n"
                                "D 行動的価値: 行動を促す構造。行動しない理由の取り除き方。最初の一歩の障壁の下げ方。再視聴・登録・共有・購入につながる仕組み。\n"
                                "最後に、4つの価値の相互作用を分析する。"),
    "p3_delivery_character": RULES + ("課題: 話術・声・キャラクター・コピーライティング。\n"
                                       "1) 声質、抑揚、テンポ、間、沈黙、強調の仕方（時刻付きの具体例）。話し方の自然さ、人間らしさ。\n"
                                       "2) 信頼形成の方法（権威、共感、実績の見せ方、誠実さの演出）。\n"
                                       "3) キャラクター（登場する時刻、役割、話の内容とのギャップ）。顔を出さないことの効果は、映像・音声から観察できる範囲と、推測とを分ける。\n"
                                       "4) コピーライティング: 問題提起→解決→未来像の型、根本的欲求（お金・自己実現・安心など）への訴求、印象的な言い回し（短く引用）。\n"
                                       "5) 映像表現: 画面構成、字幕、背景、BGM・効果音の使い方。"),
    "p4_funnel_principles": RULES + ("課題: 販売導線と、他の市場に応用できる原理。\n"
                                      "1) 動画内で確認できる販売導線・他媒体連携・収益化の手がかり（なければ「確認できない」）。\n"
                                      "2) この動画の弱点・反例になりうる点（合わない視聴者、逆効果になりうる表現）。\n"
                                      "3) 表面（話し方・キャラクター）を真似せずに抽象化できる『成功技術の原理』を5〜8個。各原理に、根拠の時刻、適用条件、他市場（美容・教育・AIサービス・デジタル商品など）への応用例、確信度（高/中/低）を付ける。\n"
                                      "4) 生身の人間である話者の強みのうち、AIで再現しやすいもの・難しいものを、観察できる範囲で分ける（結論は断定しない）。"),
}


def yt(path, **params):
    return requests.get("https://www.googleapis.com/youtube/v3/" + path, params={**params, "key": os.environ.get("YOUTUBE_API_KEY", "")}, timeout=30).json()


def main():
    vid = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-3.8-flash"
    out = d.OUT.parent / "marketing" / vid
    out.mkdir(parents=True, exist_ok=True)
    meta = {}
    v = yt("videos", part="snippet,contentDetails,statistics", id=vid)
    if v.get("items"):
        it = v["items"][0]
        ch = yt("channels", part="snippet,statistics", id=it["snippet"]["channelId"])
        c = (ch.get("items") or [{}])[0]
        meta = dict(video_id=vid, url=f"https://www.youtube.com/watch?v={vid}", title=it["snippet"]["title"], published=it["snippet"]["publishedAt"], duration=it["contentDetails"]["duration"],
                    views=it["statistics"].get("viewCount"), likes=it["statistics"].get("likeCount"), comments=it["statistics"].get("commentCount"),
                    channel=c.get("snippet", {}).get("title"), channel_subs=c.get("statistics", {}).get("subscriberCount"), channel_videos=c.get("statistics", {}).get("videoCount"),
                    description=it["snippet"].get("description", "")[:1500], tags=it["snippet"].get("tags", [])[:20], fetched_at=d.now())
    else:
        meta = dict(video_id=vid, error="metadata unavailable (未取得)", raw=v.get("error"))
    cm = yt("commentThreads", part="snippet", videoId=vid, maxResults=60, order="relevance", textFormat="plainText")
    comments = [dict(text=i["snippet"]["topLevelComment"]["snippet"]["textDisplay"][:400], likes=i["snippet"]["topLevelComment"]["snippet"].get("likeCount")) for i in cm.get("items", [])]
    meta["comments_note"] = "未取得" if not comments else f"{len(comments)} top comments by relevance (a biased sample, not all viewers)"
    (out / "meta.json").write_text(json.dumps(dict(meta=meta, comments=comments), ensure_ascii=False, indent=1), encoding="utf-8")
    print("META", json.dumps({k: meta.get(k) for k in ("title", "channel", "published", "duration", "views", "likes", "comments", "channel_subs")}, ensure_ascii=False), "| comments fetched:", len(comments), flush=True)
    uri = f"https://www.youtube.com/watch?v={vid}"
    for name, prompt in PASSES.items():
        if d.SPENT[0] > 2.5:
            print("BUDGET CAP reached; stop"); break
        r = d.gen(model, uri, None, prompt, f"{model}|{vid}|{name}", resolution="MEDIA_RESOLUTION_LOW", max_out=16000)
        (out / f"{name}.md").write_text(r["text"], encoding="utf-8")
        mod = r["usage"].get("by_modality") or {}
        print(f"PASS {name} http={r['http_status']} finish={r['finishReason']} usage={r['usage']} chars={len(r['text'])} cost={r['cost_usd']} video_or_audio_tokens={mod}", flush=True)
    (out / "raw_log.json").write_text(json.dumps(d.LOG, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TOTAL cost_usd", round(d.SPENT[0], 4))


if __name__ == "__main__":
    main()
