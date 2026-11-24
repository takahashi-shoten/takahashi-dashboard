"""Seeds the persistent marketing-knowledge DB (SQLite) from the 2026-11-24 video analyses of the channel 内田博史【金持ちの習慣】 (6 videos, Gemini analysis of picture+sound).
Every entry is an AI observation from a SMALL sample (6 of 735 videos): confidence is capped at 0.6 by knowledge.add, status stays 'observed'/'hypothesis' until market results exist.
Usage: python -m studio.seed_uchida [db_path]   (default: <repo>/knowledge/marketing_knowledge.db)"""
import sqlite3
import sys
from pathlib import Path

from . import knowledge as k

ROOT = Path(__file__).resolve().parents[2]
U = lambda v, t="": f"https://www.youtube.com/watch?v={v}" + (f"&t={t}s" if t else "")
SRC = "docs/research/uchida_analysis_2026-11-24/"
MARKET = "日本語・自己啓発/お金/脳科学系YouTube(長尺20〜26分)"
AUD = "努力しても報われないと感じている日本語話者の大人(推定)"

ENTRIES = [
    dict(category="hook", content="冒頭0〜10秒で『簡単/努力不要/常識の否定』を言い切る(例: 壁を10分見るだけで別人/モチベ不要/特別な努力でもお金や時間でもない)。6本中5本で観察、残り1本は極端な落差の実話で始まる。",
         source_url=U("JjKQjOGB6aw"), timestamp="00:00-00:11", evidence=SRC + "(各 quick.md / DYUxKuX0Bxc p1)", conditions="視聴者が『頑張っているのに報われない』不全感を持つテーマ",
         success_factors="常識の否定→続きを知りたい好奇心", failure_factors="誇大に聞こえ懐疑を招く可能性(動画内でも懐疑を代弁して先回りしている)", confidence=0.5),
    dict(category="emotion", content="『あなたの能力や性格の問題ではない』『落ち込まなくて大丈夫』と責任を外在化して罪悪感を下げてから方法を出す(6本中3本以上で観察)。",
         source_url=U("JjKQjOGB6aw", 91), timestamp="01:31-01:35", evidence=SRC + "JjKQjOGB6aw/quick.md; fxpKk4mvlqo/quick.md(01:23); r-G2ryyJIbc/quick.md(01:13)",
         conditions="自己否定が強い層", success_factors="安心→実践への心理的障壁低下", failure_factors="責任回避に聞こえる懸念(未確認)", confidence=0.5),
    dict(category="action", content="行動を極小化する(1日1分/1分でも3分でもいい/机に座るだけ/『できない』→『まだできていない』の言い換え)。コストは時間・費用・労力ほぼゼロに設定。",
         source_url=U("YzH5blXRHf8", 530), timestamp="08:50", evidence=SRC + "YzH5blXRHf8; JjKQjOGB6aw(16:48); r-G2ryyJIbc(14:59); DYUxKuX0Bxc p2(09:54)",
         conditions="行動の着手障壁が主な課題の層", success_factors="『自分にもできそう』", failure_factors="重い現実課題の根本解決力は限定的(分析自身も指摘)", confidence=0.55),
    dict(category="trust", content="海外の研究者・著者・YouTuberの知見(ケイト・ホール、ジョージ・グオ、ルーク・ベルマー、ロブ・ダイアル、F・S・シン、ドゥエック)を出典明示で日本語に再構成し権威を借りる。6本中6本。",
         source_url=U("JjKQjOGB6aw", 13), timestamp="00:13-00:18", evidence=SRC + "各動画の quick.md / p3",
         conditions="出典の知名度が視聴者に伝わること", success_factors="荒唐無稽な主張の信憑性補強", failure_factors="独自性が弱い/引用元の権利・規約は未確認/内容の正確性は未検証",
         confidence=0.5),
    dict(category="trust", content="売り込みを下げる逆張りと自虐: 『チャンネル登録しなくていい』『インチキ臭いレッサーパンダ』『ここまで聞いたあなたは頭のいい人』。視聴者を肯定して親近感・信頼を作る。",
         source_url=U("DYUxKuX0Bxc", 1328), timestamp="22:06-22:25, 25:48", evidence=SRC + "DYUxKuX0Bxc p2/p3; fxpKk4mvlqo(19:58, 24:44); JjKQjOGB6aw(21:05)",
         conditions="定型の登録依頼に飽きた/警戒心のある視聴者", success_factors="警戒心低下→コメント・メルマガへの誘導", failure_factors="効果の測定なし(登録率・維持率は未確認)", confidence=0.45),
    dict(category="retention", content="章タイトルのスライド+ほぼ全文テロップ+効果音+ストック映像/CGキャラの高頻度切替で視覚の単調さを防ぐ。末尾にNGシーンを置き人間味を残す。",
         source_url=U("JjKQjOGB6aw", 1289), timestamp="21:29", evidence=SRC + "JjKQjOGB6aw; fxpKk4mvlqo(25:19); r-G2ryyJIbc(19:14); DYUxKuX0Bxc p3",
         conditions="音声中心の長尺解説", success_factors="維持・親近感(推定)", failure_factors="視聴維持率は未確認のため効果は未検証", confidence=0.4),
    dict(category="funnel", content="導線の中心は登録者増ではなく無料メルマガ(有料セミナー動画の期間限定無料を特典)と書籍。概要欄・常時テロップ・エンドカード・口頭の複数箇所で誘導。",
         source_url=U("DYUxKuX0Bxc", 1500), timestamp="25:00-25:30", evidence=SRC + "DYUxKuX0Bxc p1/p4; JjKQjOGB6aw(20:17); fxpKk4mvlqo(19:54); r-G2ryyJIbc(18:15); YzH5blXRHf8(19:49)",
         conditions="メルマガ後の販売先がある事業", success_factors="自社リスト獲得(解釈)", failure_factors="登録率・成約・収益は未確認", confidence=0.5),
    dict(category="character", content="顔出しなしのCGレッサーパンダが、薬物・恋愛など生々しい内容を語る(キャラと内容のギャップ)。話者の素顔は出さない。効果は動画から観察できず推測のみ。",
         source_url=U("fxpKk4mvlqo", 15), timestamp="00:15-", evidence=SRC + "DYUxKuX0Bxc p3; fxpKk4mvlqo quick",
         conditions="不明", success_factors="親しみ・重い話題の中和(推測)", failure_factors="軽薄/怪しさを感じる層の離脱(動画内でも自虐的に言及)", confidence=0.35, status="hypothesis"),
    dict(category="title", content="仮説: 再生数の高い4本(74万〜110万)のタイトルは具体的な数字や日常語(1日10分/貯金3万円→60億円/めんどくさい)を含み、低い2本(4.7万・8.3万)は抽象的(どん底から億万長者/これを捨てた瞬間)。型は同じで10倍以上の差。",
         source_url=U("r-G2ryyJIbc"), timestamp="", evidence="再生数はYouTube Data APIの実測。meta.json参照。サムネイル・公開時期・チャンネル成長時期は未調査", conditions="n=6、相関のみ",
         success_factors="未確認", failure_factors="交絡(サムネイル・公開時期・アルゴリズム)が未排除", confidence=0.25, status="hypothesis"),
    dict(category="risk", content="反例/リスク: 『ヤク中』『ブス』『B専』など俗語・属性ステレオタイプ表現は、広告主・教育市場・価値観の合わない視聴者で離脱や不快のリスク。",
         source_url=U("DYUxKuX0Bxc", 34), timestamp="00:34, 13:53-14:07", evidence=SRC + "DYUxKuX0Bxc p4",
         conditions="タイアップ・公的ビジネス教育市場", success_factors="", failure_factors="ブランド毀損・ターゲットの絞り込み", confidence=0.45),
    dict(category="owner_observation", content="オーナーの観察(多数動画を視聴した上での全般的傾向。特定動画ではない): 『人生を変えるのは難しくない』という切り口→小さな良い習慣/悪習慣をやめる/不要なものを手放す→問題に気づかせる→気づいた時から変われる安心→1日1分でもいい→行動で現実が変わるに着地→納得・共感・行動意欲、繰り返し視聴する可能性。",
         source_url="https://www.youtube.com/@uchida-hiroshi/videos", timestamp="", evidence="AI分析6本との照合: 大半が一致、最後の2点(気づいた時から/視聴者の繰り返し視聴)は未確認 → docs/research/uchida_analysis_2026-11-24/",
         conditions="チャンネル全般(735本中6本のみAI分析)", success_factors="", failure_factors="", confidence=0.4, origin="owner_observation"),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "knowledge" / "marketing_knowledge.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    k.init(con)
    if con.execute("SELECT COUNT(*) FROM knowledge WHERE origin LIKE 'uchida_2026-11-24%'").fetchone()[0]:
        print("already seeded; nothing to do")
        return
    ids = []
    for e in ENTRIES:
        origin = e.pop("origin", "uchida_2026-11-24:gemini-3.8-flash")
        status = e.pop("status", "observed")
        ids.append(k.add(con, audience=AUD, market=MARKET, origin=origin if origin.startswith("owner") is False else "uchida_2026-11-24:owner_observation", status=status, **e))
    k.add_counterexample(con, ids[8], "6本はチャンネル735本の一部で、選定が偏っている(人気動画+追加1本)。タイトルが具体的でも低再生の動画が他にあるかは未確認。", url="https://www.youtube.com/@uchida-hiroshi/videos")
    k.add_counterexample(con, ids[0], "『どん底から億万長者』(83,124再生)は常識否定ではなく極端な落差の実話で始まり、再生数は上位4本の約1/9。", url=U("DYUxKuX0Bxc"))
    print("seeded", len(ids), "entries ->", path)


if __name__ == "__main__":
    main()
