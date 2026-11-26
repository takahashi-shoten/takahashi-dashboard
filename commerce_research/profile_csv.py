"""Profile commerce CSV datasets into SQLite (reuses the repo's SQLite + stdlib stats; no new framework).
Usage: python3 commerce_research/profile_csv.py DB_PATH CSV [CSV...]   -> loads each file into table raw_<n>, prints rows, missing rate per column, duplicate ids, state counts."""
import csv, sqlite3, sys, collections, json
csv.field_size_limit(10**9)

def load(con, path, table):
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f); head = next(rd)
        import re
        cols, seen = [], set()
        for i, c in enumerate(head):          # sanitize names (some sources have quotes/spaces/duplicates)
            c = re.sub(r"[^0-9A-Za-z_]+", "_", c.strip()).strip("_") or f"col{i}"
            while c in seen: c += "_"
            seen.add(c); cols.append(c)
        con.execute(f'DROP TABLE IF EXISTS "{table}"')
        con.execute(f'CREATE TABLE "{table}" (' + ",".join(f'"{c}" TEXT' for c in cols) + ", _src TEXT)")
        n = 0
        for row in rd:
            row = (row + [""] * len(cols))[:len(cols)]
            con.execute(f'INSERT INTO "{table}" VALUES (' + ",".join("?" * (len(cols) + 1)) + ")", row + [path.split("/")[-1]]); n += 1
    con.commit(); return cols, n

def profile(con, table, cols):
    n = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    miss = {c: con.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{c}" IS NULL OR TRIM("{c}")=""').fetchone()[0] / max(n, 1) for c in cols}
    idc = "id" if "id" in cols else cols[0]
    dup = n - con.execute(f'SELECT COUNT(DISTINCT "{idc}") FROM "{table}"').fetchone()[0]
    states = con.execute(f'SELECT "state",COUNT(*) FROM "{table}" GROUP BY 1 ORDER BY 2 DESC').fetchall() if "state" in cols else []
    return dict(rows=n, id_col=idc, duplicate_ids=dup, duplicate_rate=round(dup / max(n, 1), 4), states=states, missing_rate={k: round(v, 3) for k, v in miss.items() if v > 0})

if __name__ == "__main__":
    con = sqlite3.connect(sys.argv[1]); out = {}
    for i, p in enumerate(sys.argv[2:]):
        t = f"raw_{i}"; cols, n = load(con, p, t); out[p.split("/")[-1]] = dict(table=t, columns=len(cols), **profile(con, t, cols))
    print(json.dumps(out, ensure_ascii=False, indent=1))
