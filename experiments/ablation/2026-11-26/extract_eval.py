"""Extracts an evaluator agent's JSON verdict from its transcript (the final answer is in the hand-back tool call's input). Usage: extract_eval.py <agent_id> <E1|E2>"""
import json, re, sys
from pathlib import Path
T = "/tmp/claude-0/-home-user-takahashi-dashboard/dcb15c55-29fa-56df-ae95-d30276647e4f/tasks/"
aid, name = sys.argv[1:3]
txt, reads = "", 0
for line in Path(T + aid + ".output").read_text().splitlines():
    try: e = json.loads(line)
    except Exception: continue
    m = e.get("message") or {}
    if e.get("type") == "assistant" and isinstance(m.get("content"), list):
        for b in m["content"]:
            if b.get("type") == "tool_use":
                if b.get("name") == "Read": reads += 1
                if "andback" in str(b.get("name", "")):
                    vals = [v for v in (b.get("input") or {}).values() if isinstance(v, str)]
                    if vals: txt = max(vals, key=len)
mm = re.search(r"```json\s*(\{.*\})\s*```", txt, re.S)
if not mm: sys.exit("no json block found")
d = json.loads(mm.group(1))
Path(__file__).parent.joinpath("eval", f"{name}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
Path(__file__).parent.joinpath("eval", f"{name}_commentary.md").write_text(txt, encoding="utf-8")
print(name, "saved; Read calls:", reads, "tasks:", list(d))
