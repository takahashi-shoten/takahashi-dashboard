"""Persistent marketing-knowledge base (SQLite). Knowledge is stored with its evidence, searched automatically when planning/producing, and promoted or demoted by
measured market results. AI-observed single-source findings start as 'observed' with capped confidence; only market results can make them 'market_validated'."""
import json
import re
from datetime import datetime, timezone

# observed fact -> hypothesis -> supported_multi_case (several external cases) -> tested_internal -> market_validated (own market experiment) -> repeat_validated (repeated) ; invalidated = rejected/corrected
STATUSES = ("hypothesis", "observed", "supported_multi_case", "tested_internal", "market_validated", "repeat_validated", "invalidated")
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


QUALITY_COLUMNS = ("psychology", "do_not_apply", "transfer_notes", "generality", "evidence_check", "counterexample_search")


def init(con):
    con.executescript(DDL)
    have = {r[1] for r in con.execute("PRAGMA table_info(knowledge)")}
    for c in QUALITY_COLUMNS:           # additive migration: psychology link, do-not-apply conditions, transfer notes, generality (high/mid/low), evidence check, counter-example search state
        if c not in have:
            con.execute(f"ALTER TABLE knowledge ADD COLUMN {c} TEXT")
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
    order = {s: i for i, s in enumerate(("invalidated", "hypothesis", "observed", "supported_multi_case", "tested_internal", "market_validated", "repeat_validated"))}
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
        if market_result and status in ("market_validated", "repeat_validated"):
            status = "repeat_validated"            # a second market success on knowledge that was already market-validated
        else:
            status = "market_validated" if market_result and conf >= 0.7 else ("tested_internal" if status in ("hypothesis", "observed", "supported_multi_case") else status)
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

DEFAULT_DB = None   # resolved lazily: <repo>/knowledge/marketing_knowledge.db (override with env STUDIO_KNOWLEDGE_DB)
PRODUCTION_CATEGORIES = ("hook", "emotion", "action", "trust", "retention", "title", "funnel", "risk", "design_implication", "precedent_caution")


def default_db_path():
    import os
    from pathlib import Path
    p = os.environ.get("STUDIO_KNOWLEDGE_DB")
    if p:
        return Path(p) if p != "off" else None
    d = Path(__file__).resolve().parent.parent.parent / "knowledge" / "marketing_knowledge.db"
    return d if d.exists() else None


def consult(con, used_in, task="production", categories=PRODUCTION_CATEGORIES, per_category=1, audience=None):
    """Automatic lookup for planning/production by category (Japanese text is not word-split, so category is the reliable key). Strongest status/confidence first,
    invalidated excluded. Every consulted item is logged in knowledge_uses with `used_in` so later results can promote/demote it. Returns compact dicts that carry status,
    confidence, conditions and the number of counter-examples: hypotheses must stay labelled as hypotheses."""
    out = []
    for cat in categories:
        for k in search(con, "", category=cat, audience=audience, limit=per_category):
            con.execute("INSERT INTO knowledge_uses(knowledge_id,used_in,task,used_at) VALUES(?,?,?,?)", (k["knowledge_id"], used_in, task, _now()))
            out.append(dict(knowledge_id=k["knowledge_id"], category=k["category"], content=k["content"], status=k["status"], confidence=k["confidence"],
                            conditions=k["conditions"], counterexamples=len(json.loads(k["counterexamples_json"] or "[]")), source=k["source_url"]))
    con.commit()
    return out


GENERIC_TERMS = {"youtube", "ja", "日本語", "shorts", "ショート", "長尺", "動画", "instagram", "x", "web", "tiktok", "note", "booth"}   # too common to count as evidence of relevance
TASK_CATEGORIES = {
    "content_plan": ("hook", "retention", "action", "trust", "emotion", "title", "design_implication", "funnel"),
    "copy": ("hook", "emotion", "trust", "action", "title", "funnel"),
    "funnel": ("funnel", "trust", "action"),
    "product": ("emotion", "action", "trust", "funnel", "precedent_caution"),
    "decision": ("precedent", "precedent_caution", "funnel", "market_fact", "risk"),
    "qa": ("risk", "precedent_caution", "precedent", "funnel"),
}


def _row_text(r):
    return " ".join(str(r[k] or "") for k in ("content", "conditions", "audience", "market", "success_factors", "evidence")).lower()


def relevant(con, keywords, task_type=None, min_hits=2, limit=5, min_confidence=0.2):
    """Code-side selection (no LLM). Returns (items, reason). A knowledge row is returned only if (a) its category fits the task type, (b) at least `min_hits` distinct NON-generic
    keywords occur in its text (content/conditions/audience/market/evidence) - or 1 hit for a 'high' generality row, (c) no keyword occurs in its do_not_apply text, (d) it is
    not invalidated and confidence >= min_confidence. 'No relevant knowledge' is a valid result: items=[] and a reason. The use is NOT logged here (call log_use when applied)."""
    init(con)
    kws = [k.strip().lower() for k in keywords if k and k.strip().lower() not in GENERIC_TERMS]
    cats = TASK_CATEGORIES.get(task_type)
    scored = []
    for r in con.execute("SELECT * FROM knowledge"):
        if r["status"] == "invalidated" or (r["confidence"] or 0) < min_confidence:
            continue
        if cats and r["category"] not in cats:
            continue
        txt = _row_text(r)
        blocked = (r["do_not_apply"] or "").lower()
        if blocked and any(k in blocked for k in kws):
            continue
        hits = sorted({k for k in kws if k in txt})
        need = 1 if (r["generality"] or "") == "high" else min_hits
        if len(hits) >= need and hits:
            scored.append((len(hits), (r["confidence"] or 0), dict(r), hits))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    items = []
    for n, _, r, hits in scored[:limit]:
        items.append(dict(knowledge_id=r["knowledge_id"], category=r["category"], content=r["content"], status=r["status"], confidence=r["confidence"], conditions=r["conditions"],
                          do_not_apply=r["do_not_apply"], generality=r["generality"], matched_terms=hits, counterexamples=len(json.loads(r["counterexamples_json"] or "[]")), source=r["source_url"]))
    if not items:
        return [], "no relevant knowledge: no row met the category/keyword/applicability rules (this is a valid result; plan without knowledge)"
    return items, f"{len(items)} relevant item(s) selected by category + non-generic keyword match"


def log_use(con, knowledge_id, used_in, task="applied", outcome=None, detail=""):
    """Record that knowledge was actually applied (call after the planner used it)."""
    con.execute("INSERT INTO knowledge_uses(knowledge_id,used_in,task,used_at,outcome,outcome_detail) VALUES(?,?,?,?,?,?)", (knowledge_id, used_in, task, _now(), outcome, detail))
    con.commit()


def quality_checklist(con):
    """Method D: knowledge used only as a checklist (risk, failure avoidance, funnel, caution) - ids and short text for the QA stage."""
    init(con)
    out = []
    for r in con.execute("SELECT knowledge_id,category,content,status,confidence FROM knowledge WHERE category IN ('risk','precedent_caution','precedent','funnel') AND status!='invalidated' ORDER BY category,knowledge_id"):
        out.append(dict(knowledge_id=r["knowledge_id"], category=r["category"], check=r["content"][:160], status=r["status"], confidence=r["confidence"]))
    return out


def export_uses(con, path):
    """Append-only, de-duplicated JSONL of knowledge_uses (survives ephemeral Actions runs when committed to the registry branch). Returns number of new lines written."""
    from pathlib import Path
    init(con)
    p = Path(path)
    seen = set(p.read_text(encoding="utf-8").splitlines()) if p.exists() else set()
    new = []
    for r in con.execute("SELECT knowledge_id,used_in,task,used_at,outcome,outcome_detail FROM knowledge_uses ORDER BY id"):
        line = json.dumps(dict(r), ensure_ascii=False, sort_keys=True)
        if line not in seen:
            seen.add(line); new.append(line)
    if new:
        with p.open("a", encoding="utf-8") as f:
            f.write("\n".join(new) + "\n")
    return len(new)


def import_uses(con, path):
    """Merge a JSONL produced by export_uses into the DB (idempotent). Returns number of rows added."""
    from pathlib import Path
    init(con)
    p = Path(path)
    if not p.exists():
        return 0
    have = {(r[0], r[1], r[2], r[3]) for r in con.execute("SELECT knowledge_id,used_in,task,used_at FROM knowledge_uses")}
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        key = (d["knowledge_id"], d["used_in"], d["task"], d["used_at"])
        if key in have:
            continue
        con.execute("INSERT INTO knowledge_uses(knowledge_id,used_in,task,used_at,outcome,outcome_detail) VALUES(?,?,?,?,?,?)", (*key, d.get("outcome"), d.get("outcome_detail")))
        have.add(key); n += 1
    con.commit()
    return n


def apply_quality(con, entries, reason="quality review 2026-11-26"):
    """entries: {knowledge_id: {field: value, ...}} for QUALITY_COLUMNS and/or 'content' (a correction, logged in knowledge_history)."""
    init(con)
    for kid, f in entries.items():
        r = con.execute("SELECT content FROM knowledge WHERE knowledge_id=?", (int(kid),)).fetchone()
        if r is None:
            continue
        if "content" in f and f["content"] != r["content"]:
            con.execute("INSERT INTO knowledge_history(knowledge_id,at,change,old_status,new_status,old_conf,new_conf,reason) VALUES(?,?,?,?,?,?,?,?)",
                        (int(kid), _now(), "content_corrected: " + r["content"][:120], None, None, None, None, reason))
            con.execute("UPDATE knowledge SET content=?, updated_at=? WHERE knowledge_id=?", (f["content"], _now(), int(kid)))
        for c in QUALITY_COLUMNS:
            if c in f:
                con.execute(f"UPDATE knowledge SET {c}=?, updated_at=? WHERE knowledge_id=?", (f[c], _now(), int(kid)))
    con.commit()
