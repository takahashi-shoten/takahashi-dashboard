"""Script stage: Claude writes an original script + shot list + metadata, with measured cost."""
import json
import os

from . import ledger

MODEL = os.environ.get("STUDIO_SCRIPT_MODEL", "claude-opus-5-5")

SCHEMA = {
    "type": "object",
    "properties": {
        "title_options": {"type": "array", "items": {"type": "string"}},
        "original_angle": {"type": "string"},
        "hook": {"type": "string"},
        "sections": {"type": "array", "items": {
            "type": "object",
            "properties": {"heading": {"type": "string"}, "narration": {"type": "string"},
                           "visual_prompt": {"type": "string"}, "seconds": {"type": "integer"}},
            "required": ["heading", "narration", "visual_prompt", "seconds"], "additionalProperties": False}},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "fact_claims_to_verify": {"type": "array", "items": {"type": "string"}},
        "ai_disclosure_needed": {"type": "boolean"},
    },
    "required": ["title_options", "original_angle", "hook", "sections", "description", "tags",
                 "fact_claims_to_verify", "ai_disclosure_needed"],
    "additionalProperties": False,
}

SYSTEM = """You write scripts for a faceless, AI-assisted video channel. Rules:
- The video must have a clear ORIGINAL angle; never paraphrase a reference video. Reference hits only show what titles/formats get clicked.
- Write in the requested language, in a natural spoken voice. No filler, no padding to hit a length.
- Be accurate. List every factual claim that must be verified before publishing in fact_claims_to_verify. Do not invent statistics, studies or quotes.
- No sexually explicit content, nothing involving minors, no real people's likenesses, no medical promises or cures.
- visual_prompt describes an original illustration/animation shot, never a copyrighted character or a real person.
- Set ai_disclosure_needed=true when visuals or voice are synthetic and realistic."""


def write_script(con, client, project_id, target_seconds=480):
    p = con.execute("SELECT brief_json FROM projects WHERE project_id=?", (project_id,)).fetchone()
    brief = json.loads(p["brief_json"])
    user = json.dumps({"brief": brief, "target_seconds": target_seconds}, ensure_ascii=False)
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM, messages=[{"role": "user", "content": user}])
    usd = ledger.record_cost(con, project_id, "script", "anthropic", resp.model if getattr(resp, "model", None) in ledger.PRICES else MODEL,
                             resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal":
        ledger.add_step(con, project_id, "script", "failed", detail="model refused")
        return None
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    ledger.add_step(con, project_id, "script", "done", data, detail=f"cost_usd={usd:.4f}")
    con.execute("UPDATE projects SET status='script', title=? WHERE project_id=?", (data["title_options"][0], project_id))
    con.commit()
    return data
