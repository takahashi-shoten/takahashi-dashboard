"""Build a content brief from research data (ytr database). No LLM needed: pure data."""
import json
import sqlite3

from . import knowledge, ledger


def competitor_patterns(ytr_db, genre, limit=15):
    """Top recent hits in a genre from the ytr DB: titles, formats, durations (measured)."""
    c = sqlite3.connect(f"file:{ytr_db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute("""
      SELECT v.title, v.view_count, v.duration_s, v.format_class, v.published_at, ch.title AS channel
      FROM (SELECT v.*, s.view_count FROM videos v JOIN video_snapshots s ON s.video_id=v.video_id
            WHERE s.observed_at=(SELECT MAX(observed_at) FROM video_snapshots WHERE video_id=v.video_id)) v
      JOIN channels ch ON ch.channel_id=v.channel_id
      JOIN discoveries d ON d.video_id=v.video_id JOIN topics t ON t.topic_id=d.topic_id
      WHERE t.genre=? AND v.category_id!='10' AND v.view_count>=50000
      GROUP BY v.video_id ORDER BY v.view_count DESC LIMIT ?""", (genre, limit)).fetchall()
    return [dict(r) for r in rows]


def _brief_keywords(genre, audience, topic=""):
    import re
    text = " ".join([genre.replace("_", " "), audience or "", topic or ""])
    return [t for t in re.split(r"[\s、,/・]+", text) if len(t) >= 2]


def consult_knowledge(genre, lang, kb_path=None, audience="", topic="", task_type="content_plan"):
    """Relevant stored knowledge for this brief, selected by code (category + non-generic keyword match + do-not-apply rules). 'No relevant knowledge' is a valid result:
    returns ([], reason). Selection is NOT logged as a use (log_use when the planner applies it)."""
    kb_path = kb_path or knowledge.default_db_path()
    if not kb_path:
        return [], "no knowledge DB"
    kb = sqlite3.connect(str(kb_path))
    kb.row_factory = sqlite3.Row
    try:
        return knowledge.relevant(kb, _brief_keywords(genre, audience, topic), task_type)
    finally:
        kb.close()


def make_brief(ytr_db, genre, lang, platform="youtube", audience="", kb_path=None, use_knowledge=True, topic=""):
    pats = competitor_patterns(ytr_db, genre)
    kn, kn_reason = consult_knowledge(genre, lang, kb_path, audience, topic) if use_knowledge else ([], "knowledge disabled")
    durs = sorted(p["duration_s"] for p in pats if p["format_class"] == "long" and p["duration_s"])
    return dict(
        genre=genre, lang=lang, platform=platform, audience=audience,
        reference_hits=[dict(title=p["title"], views=p["view_count"], duration_s=p["duration_s"], channel=p["channel"])
                        for p in pats],
        median_long_duration_s=durs[len(durs) // 2] if durs else None,
        evidence_note="Reference titles are measured hits (YouTube Data API). They show what viewers click, "
                      "NOT what to copy: the script must add an original angle.",
        knowledge_used=kn, knowledge_selection=kn_reason,
        knowledge_note="Stored knowledge, labelled by status/confidence. 'hypothesis'/'observed' items are NOT established know-how: use as ideas to test, "
                       "respect each item's conditions, never copy surface content.",
    )


def create_project(con, brief, title=None):
    cur = con.execute("INSERT INTO projects(genre,lang,platform,title,status,brief_json,created_at) VALUES(?,?,?,?,?,?,?)",
                      (brief["genre"], brief["lang"], brief["platform"], title, "brief", json.dumps(brief, ensure_ascii=False), ledger.now()))
    con.commit()
    ledger.add_step(con, cur.lastrowid, "brief", "done", brief)
    return cur.lastrowid
