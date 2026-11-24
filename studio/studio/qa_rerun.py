"""Re-run the two-vendor QA on an existing script.json (no generation, no voice/image spend). Writes script.json + qa.json to work/rerun/.
Usage: python -m studio.qa_rerun SCRIPT_JSON [lang]     (needs ANTHROPIC_API_KEY and GEMINI_API_KEY)"""
import json
import shutil
import sys
from pathlib import Path

import anthropic

from . import qa


def main(argv=None):
    argv = argv or sys.argv[1:]
    src, lang = Path(argv[0]), (argv[1] if len(argv) > 1 else "ja")
    out = Path(__file__).resolve().parent.parent / "work" / "rerun"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, out / "script.json")
    client = anthropic.Anthropic()
    res = qa.run_qa(out, lang, [qa.WebClaudeReviewer(client), qa.GeminiReviewer()])
    (out / "qa.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("decision:", res["decision"], res["reasons"])
    for r in res["reviews"]:
        print("==", r["reviewer"], r["verdict"], r.get("usage"))
        for i in r["issues"]:
            print(" -", i[:300])
        for u in r.get("unverified_claims", []):
            print(" ?", u[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
