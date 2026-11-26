"""Builds the A (no knowledge) / B (knowledge pack) prompts for the 2026-11-26 ablation. The knowledge pack is produced by the real knowledge.consult() code path
on a COPY of the knowledge DB (the real DB's use log is written separately, after generation). Run from the repo root: python3 experiments/ablation/2026-11-26/make_prompts.py"""
import json, sqlite3, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "studio")
from studio import knowledge

HERE = Path(__file__).parent
COMMON = """あなたは小規模事業の経営・マーケティング担当のAIです。下の【状況】だけを事実として扱い、次の【課題】に答えてください。
ルール(AとB共通):
- 【状況】にない数字・固有名詞・事実を作らない。不確かなことは「未確認」「仮説」と明記する。実測と推測を分ける。
- 一般論の羅列ではなく、この状況に固有の、すぐ実行できる内容にする。費用はほぼ0円、広告費なし、人の作業は少なく。
- 景品表示法・ステルスマーケティング規制・誇大表現に反しない。
- ツールは使わない。ファイルも読まない(この指示の本文だけで答える)。回答は日本語、2,500字以内。
"""
BASE_SALON = """- 業種: 自宅1階の小さな美容室(スタイリスト3名)。着付けも受けている(卒業式の袴・成人式の振袖・七五三・浴衣)。
- 着付けの予約は現在、月2件。料金: 七五三 5,500円 / 卒業式の袴 6,600円 / 成人式の振袖 11,000円。着付け1人 45分。受けられる余力は月20人。
- Instagram: フォロワー719 / フォロー907。プロフィール文にサービス説明なし、予約リンクあり(リンク先はホットペッパービューティー)。直近6投稿のうち、着付けの投稿は0、ヘア/着付けの仕事が写る投稿は1。
- Googleマップ: 評価4.8(口コミ4件)。カテゴリ表示が不適切(「アパート」と表示)、メイン写真が不鮮明、住所が公開表示。
- ホットペッパービューティー: 掲載あり。評価5.0(口コミ8件)。着付けメニューは浴衣(ヘアセット込み7,700円)の1件のみで、オンライン予約不可(電話問い合わせ)。掲載料は未確認。
- 直近の予約は友人からのLINE(n=1)。予約の流入元の内訳は未確認。
- 目的は予約を増やすこと。撮影は週1本まで、スマホ。顔出し可。場所が特定できる映像(外観・表札・目印)は出さない。
"""
TASKS = {
 "T1": ("着付け予約の受け皿整備(集客戦略・販売導線の改善・原因分析)", BASE_SALON + "- 動画を作る前に、既にあるGoogleマップ・Instagram・ホットペッパーの『受け皿』を整えて、3週間で予約が増えるかを試したい。\n",
  """1) 現状の導線の問題を、影響が大きい順に3つ特定し、それぞれ根拠(状況のどの事実か)を書く。
2) 変更内容を具体文で出す: Googleマップの説明文(150字以内)、Instagramプロフィール文(150字以内)、予約導線の変更案(どこへ誘導し何を変えるか)。
3) 3週間の測定設計: 基準値、見る指標(3〜5個)、成功条件・停止条件・判定保留条件。サンプルが小さいことを踏まえた判定方法。
4) 最大のリスクと、やってはいけないこと。"""),
 "T2": ("着付けの実写ショート3本の企画(コンテンツ企画・冒頭の作り方)", BASE_SALON + "- 動画はYouTube ShortsとInstagramリールに同じものを出す想定。1本15〜30秒、縦型。出演は店主1名。\n",
  """1) ショート3本の企画: 各本について、題名案、冒頭10秒の台本(セリフと撮影指示)、画面上の固定見出し、締め(オチ/CTA)、撮影に必要な物。
2) 3本が互いに違う仮説を検証するように設計し、各本の仮説と、公開後に見る指標を書く。
3) 動画を見た人が予約に至るまでの導線(どこに何を置くか)。
4) 避けるべき作り方とその理由。"""),
 "T3": ("別業界の商品企画と販売コピー(顧客心理・商品企画・セールスコピー)", """- 題材: 個人事業主・フリーランス向けの、事務作業の悩み(請求書・経費・確定申告の準備など)を軽くするデジタル商品(PDF・テンプレート・チェックリスト等)を、noteまたはBOOTHで販売するテスト。
- 実行者はAI+人1名。広告費0円。作る費用は0円に近く。最初の需要テストは1〜2週間で結果が見えること。
- 第三者の分析(二次情報): デジタル商品のマーケットプレイスでは、中央値の販売者の月収は約72ドル、商品の44%は売上0。プラットフォームに出すだけでは集客と信頼がないと売れにくい。
- 既存の顧客・観客: なし(ゼロから)。ターゲットは自分で絞ってよい。
""",
  """1) ターゲットを1つに絞り、その人の悩み・感情・行動への心理的な障壁を、具体的な場面で書く(実測ではなく仮説と明記)。
2) 商品コンセプト(何を、どんな形で)、価格案、なぜその価格か。
3) 販売ページのコピー: 見出し、導入(共感)、ベネフィット、よくある反論への答え、行動を促す一文。誇大表現なし。
4) 無料でできる集客案と、1〜2週間の最小の需要テスト設計(指標、成功条件、停止条件)。"""),
 "T4": ("結果が出なかったときの原因分解と経営判断(売れない原因分析・経営判断)", BASE_SALON + """- 【試験用の仮想データ(実測ではない。判断力を試すための設定)】3週間の結果:
  * 受け皿の整備: Googleマップの表示回数 +40%、電話タップ +10%、Instagramのプロフィール訪問 +25%、予約リンクのタップ 31→34、着付けの予約 2→3件(うち流入元を答えた初回客1名は「Googleマップ」)。口コミ +2件。
  * 実写ショート3本(15〜25秒): 再生数は 800 / 1,100 / 12,400。平均視聴率は 38% / 41% / 64%。プロフィール訪問は動画公開日に合計12、予約への直接の影響は確認できず。3本目だけが冒頭で『問い』を出し、他の2本は挨拶から始まっていた。
  * 費用: AI費用0円、店主の作業時間 合計約6時間。
""",
  """1) 結果を『測れた事実』と『原因の仮説』に分け、売れない/増えない原因を(商品、顧客選び、訴求、価格、認知、集客経路、導線、信頼、制作品質)に分解して、最も可能性が高い順に並べる。仮説ごとに、確かめる方法を書く。
2) 継続・修正・撤退のどれにするかを、受け皿整備とショートそれぞれについて判断し、理由(再試行の価値と費用の比較)を書く。
3) 次の1実験(費用、期間、成功条件、停止条件)。
4) 今回の結果から再利用できる資産。"""),
}
RUBRIC_NOTE = "(評価は PREREGISTRATION.md の基準で行う)"

def pack():
    tmp = Path(tempfile.mkdtemp()) / "k.sqlite"
    shutil.copy("knowledge/marketing_knowledge.db", tmp)
    con = sqlite3.connect(tmp); con.row_factory = sqlite3.Row
    cats = [r[0] for r in con.execute("SELECT DISTINCT category FROM knowledge ORDER BY 1")]
    items = knowledge.consult(con, used_in="pack-build", task="ablation_pack_build", categories=cats, per_category=5)
    items.sort(key=lambda k: k["knowledge_id"])
    lines = ["【保存済みの知識(参考。状態・確信度・適用条件つき)】",
             "状態が『hypothesis』『observed』のものは定説ではなく、AIの観察または仮説です。適用条件が今回の状況に合わないものは使わないでください。"]
    for k in items:
        lines.append(f"- K{k['knowledge_id']} [{k['category']}] 状態={k['status']} 確信度={k['confidence']} 反例の数={k['counterexamples']}\n  内容: {k['content']}\n  適用条件: {k['conditions'] or '記載なし'}")
    return "\n".join(lines), [k["knowledge_id"] for k in items]

def main():
    (HERE / "prompts").mkdir(exist_ok=True)
    kp, ids = pack()
    (HERE / "prompts" / "knowledge_pack.txt").write_text(kp, encoding="utf-8")
    for t, (title, facts, task) in TASKS.items():
        base = f"{COMMON}\n【状況】\n{facts}\n【課題: {title}】\n{task}\n"
        (HERE / "prompts" / f"{t}_A.txt").write_text(base, encoding="utf-8")
        b = base + f"\n{kp}\n\n追加指示(B): 上の知識から、この課題に本当に役立つものだけを使い、使った知識のIDと、使わなかった主な知識とその理由を、回答の最後に『=====KNOWLEDGE_LOG=====』の行を置いてから書いてください(この部分は評価者には見せません)。\n"
        (HERE / "prompts" / f"{t}_B.txt").write_text(b, encoding="utf-8")
    print("pack ids:", ids)

if __name__ == "__main__":
    main()
