"""Live smoke test (run in GitHub Actions with ANTHROPIC_API_KEY): real script + real Claude QA, mock voice/visuals.

Prints MEASURED cost from API usage. Never prints secrets. Output files are saved under studio/work/ and uploaded as an artifact.
"""
import json
import sys

import anthropic

from . import brief, ledger, qa, script
from .run import project_dir


def main(ytr_db, genre, lang):
    con = ledger.connect(":memory:")
    b = brief.make_brief(ytr_db, genre, lang, audience="40-60代の日本人男性" if lang == "ja" else "")
    pid = brief.create_project(con, b)
    print("reference_hits:", len(b["reference_hits"]), "median_long_duration_s:", b["median_long_duration_s"])
    data = script.write_script(con, anthropic.Anthropic(), pid)
    if data is None:
        print("script: refused"); return 1
    d = project_dir(pid)
    (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("title_options:", data["title_options"])
    print("sections:", len(data["sections"]), "narration_chars:", sum(len(s["narration"]) for s in data["sections"]),
          "planned_seconds:", sum(s["seconds"] for s in data["sections"]))
    print("claims_to_verify:", len(data["fact_claims_to_verify"]), "ai_disclosure_needed:", data["ai_disclosure_needed"])
    print("narration_chars:", script.narration_chars(data), "-> est_audio_seconds:", round(script.narration_chars(data) / script.CHARS_PER_SEC.get(lang, 6.5)))
    print("HOOK:", data["hook"][:200])
    for i, sec in enumerate(data["sections"], 1):
        print(f"SECTION {i}: {sec['heading']} | {len(sec['narration'])}字 | {sec['narration'][:90]}...")
    rev = qa.WebClaudeReviewer(anthropic.Anthropic())
    res = qa.run_qa(d, lang, [rev], reference_titles=[h["title"] for h in b["reference_hits"]])
    print("qa_decision:", res["decision"], "| reasons:", res["reasons"][:3])
    for r in res["reviews"]:
        u = r.get("usage")
        if u:
            m = r.get("model") if r.get("model") in ledger.PRICES else "claude-opus-5-5"
            ledger.record_cost(con, pid, "qa", "anthropic", m, u["input_tokens"], u["output_tokens"])
        print("review:", r["reviewer"], r["verdict"], "issues:", len(r["issues"]), "unverified:", len(r["unverified_claims"]),
              "web_searches:", (u or {}).get("web_searches"))
        for it in r["issues"][:6]:
            print("  issue:", it[:200])
        for it in r["unverified_claims"][:6]:
            print("  unverified:", it[:200])
    if res["decision"] != "pass":
        issues = [i for r in res["reviews"] for i in r["issues"]]
        data2 = script.revise_with_feedback(con, anthropic.Anthropic(), pid, data, issues, res["unverified_claims"], lang)
        (d / "script.json").write_text(json.dumps(data2, ensure_ascii=False, indent=1), encoding="utf-8")
        res2 = qa.run_qa(d, lang, [qa.WebClaudeReviewer(anthropic.Anthropic())], reference_titles=[h["title"] for h in b["reference_hits"]])
        for r in res2["reviews"]:
            u = r.get("usage")
            if u:
                m = r.get("model") if r.get("model") in ledger.PRICES else "claude-opus-5-5"
                ledger.record_cost(con, pid, "qa2", "anthropic", m, u["input_tokens"], u["output_tokens"])
            print("after_revision review:", r["reviewer"], r["verdict"], "issues:", len(r["issues"]), "unverified:", len(r["unverified_claims"]))
        print("after_revision narration_chars:", script.narration_chars(data2), "| unverified_before:", len(res["unverified_claims"]),
              "-> after:", len(res2["unverified_claims"]))
    p = ledger.profit(con, pid)
    print("MEASURED_COST_USD:", round(p["cost_usd"], 4))
    for row in con.execute("SELECT stage, model, input_tokens, output_tokens, round(usd,4) usd FROM costs"):
        print("cost_row:", dict(row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
