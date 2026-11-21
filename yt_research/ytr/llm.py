"""Optional Claude API step: propose falsifiable hypotheses and new search topics.

Runs only if ANTHROPIC_API_KEY (or another SDK credential) is configured. The model can only
propose tests in the fixed metric DSL from analyze.METRICS, so every proposal is checked
against data instead of being taken on trust.
"""
import json
import os

from . import config
from .analyze import METRICS
from .util import iso, utcnow

SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "genre": {"type": "string"}, "statement": {"type": "string"},
                "metric": {"type": "string", "enum": METRICS}, "op": {"type": "string", "enum": [">=", "<="]},
                "threshold": {"type": "number"},
                "support_metric": {"type": "string", "enum": METRICS}, "min_support": {"type": "integer"}},
            "required": ["genre", "statement", "metric", "op", "threshold", "support_metric", "min_support"],
            "additionalProperties": False}},
        "topics": {"type": "array", "items": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "lang": {"type": "string"}, "region": {"type": "string"},
                           "genre": {"type": "string"}, "why": {"type": "string"}},
            "required": ["query", "lang", "region", "genre", "why"], "additionalProperties": False}},
    },
    "required": ["hypotheses", "topics"], "additionalProperties": False,
}

SYSTEM = """You analyse YouTube market research data to find under-served, non-music niches where a new,
AI-assisted channel could build repeatable (not one-off) success. You receive aggregate metrics per genre,
computed from a search *sample*, not the whole market. Propose:
- up to 6 hypotheses, each falsifiable with the given metric DSL; prefer ones that could REFUTE the most
  promising-looking genres (look for counter-evidence, not confirmation);
- up to 8 new search queries (any language/region; YouTube regionCode ISO-3166 alpha-2, lang ISO-639-1) that
  would test those hypotheses or probe adjacent unmet demand. Never propose music."""


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def propose(con, genre_metrics, max_tokens=16000):
    import anthropic  # imported lazily: optional dependency
    client = anthropic.Anthropic()
    existing = [dict(r) for r in con.execute("SELECT genre, statement, status FROM hypotheses WHERE source='llm'")]
    user = json.dumps({"genre_metrics": genre_metrics, "existing_llm_hypotheses": existing,
                       "thresholds": {"hit_views": config.MIN_VIEWS, "window_days": config.WINDOW_DAYS}},
                      ensure_ascii=False, default=str)
    resp = client.beta.messages.create(
        model=config.ANTHROPIC_MODEL, max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        thinking={"type": "adaptive"}, output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM, messages=[{"role": "user", "content": user}])
    if resp.stop_reason == "refusal":
        return {"hypotheses": [], "topics": [], "note": "refused"}
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    now = iso(utcnow())
    added_h = added_t = 0
    for i, h in enumerate(data["hypotheses"]):
        test = {k: h[k] for k in ("metric", "op", "threshold", "support_metric", "min_support")}
        hid = f"{h['genre']}:llm:{now}:{i}"
        con.execute("""INSERT OR IGNORE INTO hypotheses(hyp_id, genre, statement, test_json, source, status,
                       created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (hid, h["genre"], h["statement"], json.dumps(test), "llm", "untested", now, now))
        added_h += 1
    from .topics import add_topic
    for t in data["topics"]:
        added_t += add_topic(con, t["query"], t["lang"].lower()[:5], t["region"].upper()[:2], t["genre"], "llm", t["why"][:300])
    con.commit()
    return {"hypotheses": added_h, "topics": added_t,
            "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
