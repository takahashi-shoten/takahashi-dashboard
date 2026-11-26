"""Round 2 analysis from evaluator transcripts (only evaluators that finished). Usage: python3 analyze_round2.py"""
import json, re, statistics as st
from pathlib import Path
H = Path(__file__).parent
T = "/tmp/claude-0/-home-user-takahashi-dashboard/dcb15c55-29fa-56df-ae95-d30276647e4f/tasks/"
EVAL = {"R1": ("a900b025979ca97a7", "sonnet"), "R2": ("a0b06c93ceeb614e3", "opus"), "R3": ("a8c66149919117366", "sonnet"), "R4": ("a3975437d1b3479b3", "opus")}
maps = json.load(open(H / "blind_maps.json"))
crit = [f"C{i}" for i in range(1, 9)]
def load(aid):
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
    mm = re.search(r"```json\s*(\{.*\})\s*```", txt, re.S)
    return json.loads(mm.group(1)) if mm else None
rank = {}; score = {}; pos = {}
done = []
for ev, (aid, model) in EVAL.items():
    d = load(aid)
    if not d: print(ev, model, "NO RESULT (failed / rate-limited)"); continue
    done.append(ev); json.dump(d, open(H / "eval" / f"{ev}.json", "w"), ensure_ascii=False, indent=1)
    for t in ("T1", "T2", "T3", "T4"):
        mp = maps[ev][t]
        for r, L in enumerate(d[t]["ranking"], 1):
            rank.setdefault((mp[L], t), []).append(r); pos.setdefault(list("PQRST").index(L) + 1, []).append(r)
        for L, s in d[t]["scores"].items():
            score.setdefault((mp[L], t), []).append(sum(s[c] for c in crit) / 8)
methods = ["A", "A2", "B", "C", "D"]
print("evaluators done:", done)
print("\nmean rank (1=best) / mean score by method x task  [n evaluators = %d]" % len(done))
print("method " + " ".join(f"{t:>12}" for t in ("T1", "T2", "T3", "T4")) + "      ALL(rank/score)")
for m in methods:
    cells = [f"{st.mean(rank[(m,t)]):.2f}/{st.mean(score[(m,t)]):.2f}" for t in ("T1", "T2", "T3", "T4")]
    allr = [x for t in ("T1", "T2", "T3", "T4") for x in rank[(m, t)]]; alls = [x for t in ("T1", "T2", "T3", "T4") for x in score[(m, t)]]
    print(f"{m:>6} " + " ".join(f"{c:>12}" for c in cells) + f"      {st.mean(allr):.2f}/{st.mean(alls):.2f}")
print("\nposition effect (mean rank by presented position P..T = 1..5):", {p: round(st.mean(v), 2) for p, v in sorted(pos.items())})
print("generation noise |A2-A| (score, all tasks): %.2f" % abs(st.mean([x for t in ("T1","T2","T3","T4") for x in score[('A2',t)]]) - st.mean([x for t in ("T1","T2","T3","T4") for x in score[('A',t)]])))
