"""Append-only, verifiable snapshots of a SQLite DB (experiment registry, knowledge DB) as plain-text JSONL + schema + checksums.
Why: the current persistence overwrites (force-push, single commit) so history is lost and a bad write cannot be undone. Snapshots are new, timestamped folders that are never
modified or deleted by this module; `verify` checks every file against the manifest; `restore` refuses to touch a non-empty DB and verifies first.
Usage: python -m studio.snapshot export <db> <parent_dir> | verify <snapshot_dir> | restore <snapshot_dir> <new_db>"""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(db_path, parent_dir):
    """Write <parent_dir>/<UTC timestamp>/ with schema.sql, <table>.jsonl and manifest.json. Returns the snapshot directory."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out = Path(parent_dir) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)            # never overwrite an existing snapshot
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    ddl = [r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name")]
    (out / "schema.sql").write_text(";\n".join(ddl) + ";\n", encoding="utf-8")
    files, counts = {"schema.sql": _sha(out / "schema.sql")}, {}
    for t in tables:
        rows = [dict(r) for r in con.execute(f'SELECT rowid AS _rowid_, * FROM "{t}" ORDER BY rowid')]
        p = out / f"{t}.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        files[p.name], counts[t] = _sha(p), len(rows)
    (out / "manifest.json").write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), source=str(db_path), tables=counts, sha256=files),
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def verify(snapshot_dir):
    """Returns (ok, problems). Every file listed in the manifest must exist and match its checksum."""
    d = Path(snapshot_dir)
    try:
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, [f"manifest unreadable: {e}"]
    problems = []
    for name, digest in m["sha256"].items():
        p = d / name
        if not p.exists():
            problems.append(f"missing: {name}")
        elif _sha(p) != digest:
            problems.append(f"checksum mismatch: {name}")
    for t, n in m["tables"].items():
        p = d / f"{t}.jsonl"
        if p.exists() and sum(1 for _ in open(p, encoding="utf-8")) != n:
            problems.append(f"row count mismatch: {t}")
    return (not problems), problems


def restore(snapshot_dir, new_db_path):
    """Recreate a DB from a verified snapshot. Refuses to run if the target exists (never overwrites)."""
    ok, problems = verify(snapshot_dir)
    if not ok:
        raise ValueError("snapshot failed verification: " + "; ".join(problems))
    if Path(new_db_path).exists():
        raise FileExistsError(f"{new_db_path} already exists; restore only into a new file")
    d = Path(snapshot_dir)
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(new_db_path)
    con.executescript((d / "schema.sql").read_text(encoding="utf-8"))
    for t in m["tables"]:
        for line in open(d / f"{t}.jsonl", encoding="utf-8"):
            r = json.loads(line)
            cols = [c for c in r if c != "_rowid_"]
            con.execute(f'INSERT INTO "{t}"(rowid,{",".join(chr(34) + c + chr(34) for c in cols)}) VALUES(?,{",".join("?" * len(cols))})', [r["_rowid_"]] + [r[c] for c in cols])
    con.commit()
    con.close()
    return m["tables"]


def main(argv=None):
    a = argv or sys.argv[1:]
    if a[:1] == ["export"]:
        print(export(a[1], a[2]))
    elif a[:1] == ["verify"]:
        ok, p = verify(a[1])
        print("OK" if ok else "FAILED: " + "; ".join(p))
        return 0 if ok else 1
    elif a[:1] == ["restore"]:
        print(restore(a[1], a[2]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
