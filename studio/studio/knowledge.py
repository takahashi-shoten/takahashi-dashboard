"""Persistent marketing-knowledge base (SQLite). Knowledge is stored with its evidence, searched automatically when planning/producing, and promoted or demoted by
measured market results. AI-observed single-source findings start as 'observed' with capped confidence; only market results can make them 'market_validated'."""
import json
import re
from datetime import datetime, timezone

STATUSES = ("hypothesis", "observed", "tested_internal", "market_validated", "invalidated")
DDL = """
CREATE TABLE IF NOT EXISTS knowledge(
  knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT, evidence TEXT, source_url TEXT, timestamp TEXT, observed_at TEXT,
  audience TEXT, market TEXT, conditions TEXT, success_factors TEXT, failure_factors TEXT, counterexamples_json TEXT DEFAULT '[]',
  confidence REAL, status TEXT, origin TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER, at TEXT, change TEXT, old_status TEXT, new_status TEXT, old_conf REAL, new_conf REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS knowledge_uses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER, used_in TEXT, task TEXT, used_at TEXT, outcome TEXT, outcome_detail TEXT);
"""
SINGLE_SOURCE_CAP = 0.6


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init(con):
    con.executescript(DDL)
    con.commit()


def add(con, category, content, source_url=None, timestamp=None, evidence="", audience="", market="", conditions="", success_factors="", failure_factors="",
        confidence=0.4, status="observed", origin="ai_observation"):
    if status not in STATUSES:
        raise ValueError(status)
    init(con)
    conf = min(confidence, SINGLE_SOURCE_CAP) if status in ("observed", "hypothesis") else confidence
    cur = con.execute("INSERT INTO knowledge(category,content,evidence,source_url,timestamp,observed_at,audience,market,conditions,success_factors,failure_factors,"
                      "confidence,status,origin,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (category, content, evidence, source_url, timestamp, _now(), audience, market, conditions, success_factors, failure_factors, conf, status, origin, _now(), _now()))
    kid = cur.lastrowid
    con.execute("INSERT INTO knowledge_history(knowledge_id,at,change,new_status,new_conf,reason) VALUES(?,?,?,?,?,?)", (kid, _now(), "created", status, conf, origin))
    con.commit()
    return kid


def ingest_analysis(con, analysis, url, audience="", market=""):
    """analysis: dict with 'findings' as returned by video_analysis. Only findings with an observed fact become knowledge; interpretation is kept as such."""
    n = 0
    for f in (analysis or {}).get("findings", []):
        if not f.get("observed_fact"):
            continue
        content = f"[{f.get('category')}] {f['observed_fact']}" + (f" -> (interpretation) {f['interpretation']}" if f.get("interpretation") else "")
        add(con, f.get("category", "unknown"), content, source_url=url, timestamp=f.get("time"), evidence=f.get("evidence", ""), audience=audience, market=market,
            confidence=float(f.get("confidence", 0.4)), status="observed", origin=f"video_analysis:{f.get('source', '?')}")
        n += 1
    return n


def _tokens(q):
    return [t for t in re.split(r"[\s,、。/]+", q.lower()) if t]


def search(con, query="", category=None, audience=None, include_invalidated=False, limit=10):
    """Keyword search ranked by term hits, then status strength, then confidence. Invalidated knowledge is excluded unless asked for."""
    init(con)
    rows = con.execute("SELECT * FROM knowledge").fetchall()
    toks = _tokens(query)
    order = {s: i for i, s in enumerate(("invalidated", "hypothesis", "observed", "tested_internal", "market_validated"))}
    out = []
    for r in rows:
        if r["status"] == "invalidated" and not include_invalidated:
            continue
        if category and r["category"] != category:
            continue
        if audience and audience not in (r["audience"] or ""):
            continue
        hay = " ".join(str(r[k] or "") for k in ("content", "evidence", "conditions", "success_factors", "category")).lower()
        score = sum(hay.count(t) for t in toks) if toks else 1
        if score:
            out.append((score, order[r["status"]], r["confidence"] or 0, r))
    out.sort(key=lambda x: (-x[0], -x[1], -x[2]))
    return [dict(x[3]) for x in out[:limit]]


def for_task(con, task, context="", limit=5, used_in=None):
    """The automatic lookup used by planning/production: returns knowledge and records that it was consulted (so decisions can be traced)."""
    found = search(con, f"{task} {context}", limit=limit)
    for k in found:
        con.execute("INSERT INTO knowledge_uses(knowledge_id,used_in,task,used_at) VALUES(?,?,?,?)", (k["knowledge_id"], used_in, task, _now()))
    con.commit()
    return found


def record_outcome(con, knowledge_id, used_in, outcome, detail="", market_result=False):
    """outcome: 'worked' | 'failed' | 'inconclusive'. Market results move status/confidence; internal results never reach market_validated."""
    r = con.execute("SELECT status, confidence FROM knowledge WHERE knowledge_id=?", (knowledge_id,)).fetchone()
    con.execute("INSERT INTO knowledge_uses(knowledge_id,used_in,task,used_at,outcome,outcome_detail) VALUES(?,?,?,?,?,?)", (knowledge_id, used_in, "outcome", _now(), outcome, detail))
    status, conf = r["status"], r["confidence"] or 0.4
    if outcome == "worked":
        conf = min(0.95 if market_result else 0.7, conf + 0.15)
        status = "market_validated" if market_result and conf >= 0.7 else ("tested_internal" if status in ("hypothesis", "observed") else status)
    elif outcome == "failed":
        conf = max(0.05, conf - 0.25)
        if market_result and conf <= 0.2:
            status = "invalidated"
    con.execute("UPDATE knowledge SET status=?, confidence=?, updated_at=? WHERE knowledge_id=?", (status, conf, _now(), knowledge_id))
    con.execute("INSERT INTO knowledge_history(knowledge_id,at,change,old_status,new_status,old_conf,new_conf,reason) VALUES(?,?,?,?,?,?,?,?)",
                (knowledge_id, _now(), "outcome:" + outcome, r["status"], status, r["confidence"], conf, detail))
    con.commit()


def add_counterexample(con, knowledge_id, description, url=None):
    r = con.execute("SELECT counterexamples_json FROM knowledge WHERE knowledge_id=?", (knowledge_id,)).fetchone()
    lst = json.loads(r[0] or "[]") + [dict(description=description, url=url, at=_now())]
    con.execute("UPDATE knowledge SET counterexamples_json=?, updated_at=? WHERE knowledge_id=?", (json.dumps(lst, ensure_ascii=False), _now(), knowledge_id))
    con.commit()
