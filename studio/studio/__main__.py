"""python -m studio brief --ytr-db X --genre cozy_life --lang en | script --project N | status --project N"""
import argparse
import json

from . import brief, ledger, pipeline, script


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio")
    ap.add_argument("cmd", choices=["brief", "script", "status", "profit", "demo"])
    ap.add_argument("--ytr-db"); ap.add_argument("--genre"); ap.add_argument("--lang", default="ja")
    ap.add_argument("--project", type=int)
    a = ap.parse_args(argv)
    con = ledger.connect()
    if a.cmd == "brief":
        b = brief.make_brief(a.ytr_db, a.genre, a.lang)
        print("project", brief.create_project(con, b), "reference_hits", len(b["reference_hits"]))
    elif a.cmd == "script":
        import anthropic
        d = script.write_script(con, anthropic.Anthropic(), a.project)
        print(json.dumps(d, ensure_ascii=False, indent=1)[:3000] if d else "no script")
        print(ledger.profit(con, a.project))
    elif a.cmd == "demo":
        from . import run
        print(json.dumps(run.demo(), ensure_ascii=False, indent=1))
    elif a.cmd == "status":
        for stage, s, note in pipeline.status(con, a.project):
            print(f"{stage:9} {s:14} {note}")
    else:
        print(ledger.profit(con, a.project))


if __name__ == "__main__":
    main()
