"""Round 2: extract the 12 new outputs from agent transcripts, then build blinded evaluation inputs (5 methods x 4 tasks, order rotated per evaluator, seed 20261126)."""
import json, random, re
from pathlib import Path
H = Path(__file__).parent; R1 = H.parent / "2026-11-26"
T = "/tmp/claude-0/-home-user-takahashi-dashboard/dcb15c55-29fa-56df-ae95-d30276647e4f/tasks/"
IDS = {"T1_A2": "ad14f816aa3ad6120", "T1_C": "a298e867993c50b73", "T1_D": "ae3ac1b7e167bc54d", "T2_A2": "af4dbf023e136eac1", "T2_C": "a36737cd6fd076125", "T2_D": "af39707f7d1901dd3",
       "T3_A2": "a45cc1300bfd09d0c", "T3_C": "a10e26d546f8273d8", "T3_D": "abe7cf5db07674500", "T4_A2": "ab3d4cd3f9d9e736d", "T4_C": "a7b2ebba37114d159", "T4_D": "ad9ac07952d691550"}
out = H / "outputs"; out.mkdir(exist_ok=True)
for k, aid in IDS.items():
    txt = ""
    for line in Path(T + aid + ".output").read_text().splitlines():
        try: e = json.loads(line)
        except Exception: continue
        m = e.get("message") or {}
        if e.get("type") == "assistant" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if b.get("type") == "tool_use" and "andback" in str(b.get("name", "")):
                    vals = [v for v in (b.get("input") or {}).values() if isinstance(v, str)]
                    if vals: txt = max(vals, key=len)
    (out / f"{k}.txt").write_text(txt, encoding="utf-8")
def body(t, m):
    p = (out / f"{t}_{m}.txt") if m in ("A2", "C", "D") else (R1 / "outputs" / f"{t}_{m}.txt")
    s = p.read_text(encoding="utf-8")
    s = re.split(r"=====(KNOWLEDGE_LOG|CHANGES)=====", s)[0].rstrip()
    s = re.sub(r"[\((]K\d+(、K\d+)*[\))]", "", s).replace("(K9は仮説止まり)", "(仮説止まり)").replace("K18はn=1の観察で、これが", "これは1店舗の観察で、これが")
    return s
rubric = open(R1 / "PREREGISTRATION.md", encoding="utf-8").read()
rubric = rubric[rubric.index("- 各出力を、次の8基準"):rubric.index("## 判定ルール")]
rng = random.Random(20261126)
methods = ["A", "A2", "B", "C", "D"]
base = {t: rng.sample(methods, 5) for t in ("T1", "T2", "T3", "T4")}
maps = {}
for ev in range(4):
    order = {t: base[t][ev:] + base[t][:ev] for t in base}
    letters = "PQRST"
    maps[f"R{ev+1}"] = {t: dict(zip(letters, order[t])) for t in order}
    parts = ["# 評価用の入力(匿名・第2回)\nあなたは独立した評価者です。各課題に、同じ課題への5つの回答(P〜T)があります。どう作られたかは分かりません。推測せず内容だけで評価してください。\n\n"
             "## 評価基準\n" + rubric + "\n\n## 追加: 順位\n課題ごとに、5つを最良から最悪の順(1位〜5位)に並べてください(同順位なし)。\n\n"
             "## 出力形式(厳守)\n最後に次のJSONだけを1つの```json ブロックで出力する(その前に課題ごとの短い講評は書いてよい)。\n"
             "```json\n{\"T1\":{\"scores\":{\"P\":{\"C1\":0,\"C2\":0,\"C3\":0,\"C4\":0,\"C5\":0,\"C6\":0,\"C7\":0,\"C8\":0},\"Q\":{...},\"R\":{...},\"S\":{...},\"T\":{...}},\"fabricated_facts\":{\"P\":0,\"Q\":0,\"R\":0,\"S\":0,\"T\":0},\"ranking\":[\"P\",\"Q\",\"R\",\"S\",\"T\"],\"reason\":\"…\"},\"T2\":{…},\"T3\":{…},\"T4\":{…}}\n```\n"]
    for t in ("T1", "T2", "T3", "T4"):
        task = (R1 / "prompts" / f"{t}_A.txt").read_text(encoding="utf-8")
        parts.append(f"\n\n---\n# 課題 {t}\n以下が回答者に与えられた課題文(今日の日付は 2026-11-26 で、これは事実)。\n\n{task}\n")
        for L in letters:
            parts.append(f"\n## 回答{L}\n{body(t, maps[f'R{ev+1}'][t][L])}\n")
    (H / "eval").mkdir(exist_ok=True)
    (H / "eval" / f"eval_input_R{ev+1}.md").write_text("".join(parts), encoding="utf-8")
json.dump(maps, open(H / "blind_maps.json", "w"), ensure_ascii=False, indent=1)
print({k: v["T1"] for k, v in maps.items()})
for ev in range(4):
    s = (H / "eval" / f"eval_input_R{ev+1}.md").read_text(encoding="utf-8")
    print(ev + 1, len(s), "K-ids left:", len(re.findall(r"K\d", s)), "CHANGES left:", s.count("CHANGES"))
