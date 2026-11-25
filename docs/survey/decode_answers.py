"""Decode the answer code that the survey's 'LINEで送る' button produces. Usage: python3 decode_answers.py <file-with-the-pasted-LINE-text>  (or paste on stdin).
Each line is  id=value : yes/no (0=はい,1=いいえ,2=分からない), single choice / multi choice (option numbers, 0 = first), scale (0-4 -> 1-5), numbers, short text."""
import json
import re
import sys
from pathlib import Path

d = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))
Q = {q["id"]: (s["h"], q) for s in d["S"] for q in s["qs"]}
text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
seen = set()
for line in text.splitlines():
    m = re.match(r"^([a-z]\d+)=(.*)$", line.strip())
    if not m or m[1] not in Q:
        continue
    qid, v = m[1], m[2].strip()
    h, q = Q[qid]
    ty = q["ty"]
    try:
        if ty == "yn":
            a = d["YN"][int(v)]
        elif ty == "sc":
            a = f"{int(v) + 1} / 5"
        elif ty == "sg":
            a = q["o"][int(v)]
        elif ty == "ch":
            a = "、".join(q["o"][int(i)] for i in v.split(",") if i != "")
        elif ty == "num":
            a = f"{v} {q.get('u', '')}"
        else:
            a = v
    except (ValueError, IndexError):
        a = f"(読み取れない: {v})"
    seen.add(qid)
    print(("★" if q.get("star") else "・") + f"[{h}] {q['t']} → {a}")
missing = [i for i, (h, q) in Q.items() if q.get("star") and i not in seen]
print("\n未回答の★:", ", ".join(missing) or "なし")
