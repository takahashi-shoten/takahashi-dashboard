"""Marketing / sales-copy engine (minimal first slice).

Generates several copy variants per piece of content (title, thumbnail text, opening hook, CTA), each labelled with the
marketing principle used and an explanation for the owner. Every variant is stored as an experiment so results can be
compared later; verdicts are only 'winner' when the data is sufficient, never on a hunch.

Evidence rule: a claim is tagged `measured` only if it comes from data passed in (e.g. research DB hits); everything else is `hypothesis`.
Nothing here posts, sends or spends: it only writes proposals and records results the owner/pipeline reports.
"""
import json
import math
import os

from . import ledger

MODEL = os.environ.get("STUDIO_COPY_MODEL", "claude-opus-5-5")

PRINCIPLES = {
    "AIDA": "注意(Attention)→関心(Interest)→欲求(Desire)→行動(Action)の順に引っ張る型。",
    "PAS": "問題(Problem)を突き、悪化(Agitate)させて、解決(Solution)を示す型。悩み解決系に強い。",
    "benefit": "機能ではなく、見た人が得る結果(ベネフィット)を先に言う。",
    "curiosity_gap": "答えを少し隠して「続きが知りたい」を作る。ただし答えが空だと離脱と不信につながる。",
    "specificity": "数字・固有名詞など具体的な情報で信頼と注目を得る。",
    "contrast": "意外な対比(常識と事実のずれ)で止まらせる。",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "audience": {"type": "string"}, "pain_or_desire": {"type": "string"},
        "variants": {"type": "array", "items": {"type": "object", "properties": {
            "principle": {"type": "string", "enum": list(PRINCIPLES)},
            "title": {"type": "string"}, "thumbnail_text": {"type": "string"},
            "hook": {"type": "string"}, "cta": {"type": "string"},
            "why_ja": {"type": "string"},
            "evidence_basis": {"type": "string", "enum": ["measured", "hypothesis"]},
            "claims_to_verify": {"type": "array", "items": {"type": "string"}}},
            "required": ["principle", "title", "thumbnail_text", "hook", "cta", "why_ja", "evidence_basis", "claims_to_verify"],
            "additionalProperties": False}},
        "recommended_index": {"type": "integer"},
        "learning_note_ja": {"type": "string"},
    },
    "required": ["audience", "pain_or_desire", "variants", "recommended_index", "learning_note_ja"],
    "additionalProperties": False,
}

SYSTEM = """You are a direct-response marketer and sales copywriter for a business that earns from video content (ads, affiliate, own products).
Write 4-5 copy variants for ONE piece of content, each using a DIFFERENT principle from the allowed list.
Rules:
- Never promise income or results you cannot back up; no invented statistics, testimonials or achievements; no exaggerated claims. Finance/health: general education only, no individual advice.
- The title must be answerable by the content: do not tease something the video does not deliver.
- evidence_basis is "measured" only if the supplied evidence (measured_patterns / past_lessons) supports the choice; otherwise "hypothesis".
- why_ja: 1-2 short sentences in Japanese explaining to a non-expert owner why this copy should work and which principle it uses.
- claims_to_verify: factual claims in the copy that must be checked against sources before publishing.
- learning_note_ja: one short Japanese lesson for the owner (what to look at in the numbers to judge these variants)."""

DDL = """
CREATE TABLE IF NOT EXISTS experiments(
  experiment_id INTEGER PRIMARY KEY AUTOINCREMENT, grp TEXT, project_id INTEGER, goal TEXT, lang TEXT,
  principle TEXT, copy_json TEXT, evidence_basis TEXT, status TEXT, metric TEXT, impressions INTEGER, successes INTEGER,
  verdict TEXT, lesson TEXT, created_at TEXT);
"""


def init(con):
    con.executescript(DDL)
    con.commit()


def past_lessons(con, goal=None, limit=12):
    init(con)
    rows = con.execute("SELECT principle,verdict,lesson,metric,impressions,successes FROM experiments WHERE verdict IN ('winner','loser') "
                       + ("AND goal=? " if goal else "") + "ORDER BY experiment_id DESC LIMIT ?",
                       ((goal, limit) if goal else (limit,))).fetchall()
    return [dict(r) for r in rows]


def generate_copy(con, client, project_id, topic, lang, goal="watch_or_click", measured_patterns=None):
    """Ask the model for copy variants and store each as a proposed experiment. Returns (group_id, result)."""
    init(con)
    payload = {"topic": topic, "lang": lang, "goal": goal, "allowed_principles": PRINCIPLES,
               "measured_patterns": measured_patterns or [], "past_lessons": past_lessons(con, goal)}
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=8000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    ledger.record_cost(con, project_id, "copy", "anthropic", MODEL, resp.usage.input_tokens, resp.usage.output_tokens)
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    grp = f"{project_id}-{ledger.now()}"
    for v in data["variants"]:
        con.execute("INSERT INTO experiments(grp,project_id,goal,lang,principle,copy_json,evidence_basis,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (grp, project_id, goal, lang, v["principle"], json.dumps(v, ensure_ascii=False), v["evidence_basis"], "proposed", ledger.now()))
    con.commit()
    return grp, data


def _z_two_prop(s1, n1, s2, n2):
    p = (s1 + s2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) if 0 < p < 1 else 0
    return 0.0 if se == 0 else (s1 / n1 - s2 / n2) / se


def record_result(con, experiment_id, metric, impressions, successes):
    con.execute("UPDATE experiments SET metric=?,impressions=?,successes=?,status='measured' WHERE experiment_id=?",
                (metric, impressions, successes, experiment_id))
    con.commit()


def judge_group(con, grp, min_n=1000):
    """Compare measured variants of one group. 'winner/loser' only if every variant has >= min_n impressions and |z| >= 1.96; otherwise 'inconclusive'."""
    rows = con.execute("SELECT * FROM experiments WHERE grp=? AND status='measured'", (grp,)).fetchall()
    if len(rows) < 2:
        return {"verdict": "need_more_variants_measured", "n": len(rows)}
    if any(r["impressions"] < min_n for r in rows):
        verdict = "inconclusive"; reason = f"impressions < {min_n} on at least one variant: too little data to call a winner"
    else:
        rows = sorted(rows, key=lambda r: -r["successes"] / r["impressions"])
        best, worst = rows[0], rows[-1]
        z = _z_two_prop(best["successes"], best["impressions"], worst["successes"], worst["impressions"])
        if abs(z) >= 1.96:
            verdict = "decided"; reason = f"z={z:.2f} between best ({best['principle']}) and worst ({worst['principle']})"
            for r in rows:
                v = "winner" if r["experiment_id"] == best["experiment_id"] else ("loser" if r["experiment_id"] == worst["experiment_id"] else "neutral")
                con.execute("UPDATE experiments SET verdict=?,lesson=? WHERE experiment_id=?", (v, f"{reason}; rate={r['successes']/r['impressions']:.4f}", r["experiment_id"]))
            con.commit()
        else:
            verdict = "inconclusive"; reason = f"z={z:.2f}: difference not significant"
    return {"verdict": verdict, "reason": reason}
