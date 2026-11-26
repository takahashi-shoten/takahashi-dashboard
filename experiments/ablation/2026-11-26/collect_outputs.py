"""Extracts each generation agent's final answer from its transcript file (no retyping) into outputs/<task>_<cond>.txt. Usage: python3 collect_outputs.py"""
import json, sys
from pathlib import Path
T = "/tmp/claude-0/-home-user-takahashi-dashboard/dcb15c55-29fa-56df-ae95-d30276647e4f/tasks/"
IDS = {"T1_A": "ab0e2844612575a7d", "T1_B": "a48878a9c1d21f563", "T2_A": "a7f45ddc3c2596b9e", "T2_B": "a0e5c7cdbd31d1547",
       "T3_A": "a162e00e6eb0f2406", "T3_B": "a9b369c398327d076", "T4_A": "ace549e79d8c46989", "T4_B": "ab47e1d9fb99c90d0"}
out = Path(__file__).parent / "outputs"; out.mkdir(exist_ok=True)
for k, aid in IDS.items():
    p = Path(T + aid + ".output")
    if not p.exists():
        print(k, "missing"); continue
    last, tools = None, 0
    for line in p.read_text().splitlines():
        try: e = json.loads(line)
        except Exception: continue
        m = e.get("message") or {}
        if e.get("type") == "assistant" and isinstance(m.get("content"), list):
            txt = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
            tools += sum(1 for b in m["content"] if b.get("type") == "tool_use" and b.get("name") in ("Read", "Bash", "Grep", "Glob", "WebSearch", "WebFetch"))
            for b in m["content"]:           # the final answer is delivered through the hand-back tool call's input
                if b.get("type") == "tool_use" and "andback" in str(b.get("name", "")):
                    vals = [v for v in (b.get("input") or {}).values() if isinstance(v, str)]
                    if vals: txt = max(vals, key=len)
            if txt.strip(): last = txt
    if last:
        (out / f"{k}.txt").write_text(last, encoding="utf-8"); print(k, len(last), "chars, tool_uses:", tools)
    else:
        print(k, "no final text yet")
