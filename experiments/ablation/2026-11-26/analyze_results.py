"""Applies the pre-registered analysis (PREREGISTRATION.md) to eval/E1.json, eval/E2.json using blind_map.json. Prints per-task B-A rubric differences,
preferences and the pre-registered verdict. Usage: python3 analyze_results.py"""
import json
from pathlib import Path
H = Path(__file__).parent
import sys
MAP = sys.argv[1] if len(sys.argv) > 1 else "blind_map.json"
NAMES = tuple(sys.argv[2:]) or ("E1", "E2")
bm = json.load(open(H / MAP))
crit = [f"C{i}" for i in range(1, 9)]
ev = {n: json.load(open(H / "eval" / f"{n}.json")) for n in NAMES if (H / "eval" / f"{n}.json").exists()}
rows, wins = [], {}
for t in ("T1", "T2", "T3", "T4"):
    for n, e in ev.items():
        r = e[t]; m = bm[t]
        a_key = "X" if m["X"] == "A" else "Y"; b_key = "X" if m["X"] == "B" else "Y"
        diff = {c: r[b_key][c] - r[a_key][c] for c in crit}
        pref = r["preferred"]; side = "tie" if pref == "tie" else ("B" if pref == b_key else "A")
        fab = (r["fabricated_facts"][a_key], r["fabricated_facts"][b_key])
        rows.append((t, n, diff, side, fab, r.get("reason", "")))
        wins.setdefault(t, []).append(side)
print("task eval  " + " ".join(f"{c:>4}" for c in crit) + "  mean  pref  fab(A,B)")
for t, n, d, side, fab, _ in rows:
    mean = sum(d.values()) / len(d)
    print(f"{t}   {n}   " + " ".join(f"{d[c]:+4d}" for c in crit) + f"  {mean:+.2f}  {side:>4}  {fab}")
print()
verdict = {}
for t, s in wins.items():
    verdict[t] = s[0] if len(set(s)) == 1 and len(s) == 2 else "判定不能(割れ)"
print("per-task (both evaluators agree?):", verdict)
b_tasks = sum(1 for v in verdict.values() if v == "B")
c2 = [d["C2"] for _, _, d, *_ in rows]
print(f"B preferred by both evaluators in {b_tasks}/4 tasks; mean C2 diff {sum(c2)/len(c2):+.2f}")
print("PRE-REGISTERED VERDICT:", "改善を示した(予備評価)" if b_tasks >= 3 and sum(c2) / len(c2) >= 0 else "改善は示されなかった")
