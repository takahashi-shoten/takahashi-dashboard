"""Round 2: knowledge-use methods. Reuses round-1 outputs (A = independent plan) and the same knowledge pack. Methods:
 A  : no knowledge (round-1 output, reused)      A2: replicate of A (generation variance)       B: knowledge before planning (round-1 output, reused)
 C  : independent plan (=A) then reconcile with knowledge, fix only what it clearly improves
 D  : keep the plan; use knowledge only as a fact/quality/failure-avoidance/funnel checklist (derived from knowledge ids below)
Run from repo root: python3 experiments/ablation/2026-11-26-round2/make_prompts.py"""
from pathlib import Path
R1 = Path("experiments/ablation/2026-11-26"); HERE = Path(__file__).parent
pack = (R1 / "prompts" / "knowledge_pack.txt").read_text(encoding="utf-8")
CHECKLIST = """【品質チェックリスト(保存済みの知識から作成。企画の内容を変えるためではなく、誤りや抜けを見つけるためだけに使う)】
1. 誇大表現・断定・ステルスマーケティング・属性や俗語への配慮の欠如がないか(K10、規約)。
2. 他者の映像・著作物の転載や、権利の不明な素材に依存していないか。自作・実写・自社素材か(K14)。
3. 重要な行動(公開・支払い・設定変更)の前に確認や承認の手順があるか。AI自身の評価だけに頼っていないか(K16)。
4. 自己申告・二次情報・仮想データを、事実や根拠のように扱っていないか(K17)。
5. 発信から行動(予約・購入)までの導線に断絶がないか。導線の最後の地点で、目的のメニュー・商品を選べて申し込めるか。無料の入口と、その先の受け皿があるか(K18・K7)。
6. 平均でなく中央値で見る、外れ値1件を成功の根拠にしない、標本が小さいことを踏まえた判定か(K12)。
7. 見出しやタイトルは、具体的な変化・損失・数字が一目で分かるか(K9。ただし仮説・確信度低)。
"""
COMMON_TAIL = "ルール: 【状況】にない数字・固有名詞・事実を作らない(今日の日付は 2026-11-26 で、これは事実)。ツールは使わない。ファイルも読まない(この指示の本文だけで答える)。日本語。最終版は2,500字以内。\n"
for t in ("T1", "T2", "T3", "T4"):
    a_prompt = (R1 / "prompts" / f"{t}_A.txt").read_text(encoding="utf-8")
    a_out = (R1 / "outputs" / f"{t}_A.txt").read_text(encoding="utf-8")
    (HERE / "prompts").mkdir(exist_ok=True)
    (HERE / "prompts" / f"{t}_A2.txt").write_text(a_prompt, encoding="utf-8")
    task = a_prompt
    c = f"""あなたは小規模事業の経営・マーケティング担当のAIです。下に、同じ課題に対する前の担当者の企画(【前の企画】)があります。
あなたの役割: この企画を、保存済みの知識(【保存済みの知識】)と照合し、**適用条件が今回の状況に合い、かつ企画を明確に良くできる箇所だけ**を修正した最終版を出すことです。
- 企画の方向・構成を、知識を使うためだけに変えない。無関係な知識は使わない。改善できなければ、その箇所は変えない。変更が1つもなくてもよい。
- 課題文(状況と事実)は変わらない。事実にない数字を作らない。
{COMMON_TAIL}
出力: 最終版の全文を書き、その後に『=====CHANGES=====』の行を置いて、(a)使った知識のIDと、そのIDでどこをどう直したか (b)知識を見たが変えなかった主な箇所とその理由 を書く(この部分は評価者には見せない)。

【課題文(前の担当者に与えたもの)】
{task}
【前の企画】
{a_out}

{pack}
"""
    d = f"""あなたは小規模事業の経営・マーケティング担当のAIです。下に、同じ課題に対する前の担当者の企画(【前の企画】)があります。
あなたの役割: 企画の方向・構成・内容は**変えずに**、【品質チェックリスト】だけで企画を点検し、問題がある箇所だけを最小限に直した最終版を出すことです。
- チェックで問題が見つからなければ、変更しない(変更ゼロでもよい)。新しい企画や新しい要素を足さない。チェックリストにない観点での書き換えもしない。
{COMMON_TAIL}
出力: 最終版の全文を書き、その後に『=====CHANGES=====』の行を置いて、(a)どのチェック項目で、どこを、どう直したか (b)問題なしと判断した項目 を書く(この部分は評価者には見せない)。

【課題文(前の担当者に与えたもの)】
{task}
【前の企画】
{a_out}

{CHECKLIST}
"""
    (HERE / "prompts" / f"{t}_C.txt").write_text(c, encoding="utf-8")
    (HERE / "prompts" / f"{t}_D.txt").write_text(d, encoding="utf-8")
print("ok")
