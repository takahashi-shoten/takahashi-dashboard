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

CHARS_PER_SEC = {"ja": 6.5, "en": 15.0}   # speaking speed assumption; recalibrated from measured VOICEVOX output later
LENGTH_TOLERANCE = 0.15

SYSTEM = """You write scripts for a faceless, AI-assisted video channel. Rules:
- The video must have a clear ORIGINAL angle; never paraphrase a reference video. Reference hits only show what titles/formats get clicked.
- Write in the requested language, in a natural spoken voice. No filler, no padding to hit a length.
- Be accurate. List every factual claim that must be verified before publishing in fact_claims_to_verify. Do not invent statistics, studies or quotes.
- No sexually explicit content, nothing involving minors, no real people's likenesses, no medical promises or cures.
- visual_prompt describes an original illustration/animation shot, never a copyrighted character or a real person.
- Set ai_disclosure_needed=true when visuals or voice are synthetic and realistic.
- LENGTH IS A HARD REQUIREMENT: the total number of characters in all `narration` fields must be within 10% of `target_narration_chars`
  (count characters, not words). Do not summarize or stop early; develop each section fully with examples and concrete detail.
  Set each section's `seconds` to its narration characters divided by `chars_per_second`, rounded."""
REVISE_SYSTEM = SYSTEM + """
You are REVISING an existing script. Return the complete revised script in the same schema. Follow the instruction exactly."""


def narration_chars(data):
    return sum(len(s["narration"]) for s in data["sections"])


def _call(con, client, project_id, stage, system, payload):
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    usd = ledger.record_cost(con, project_id, stage, "anthropic", resp.model if getattr(resp, "model", None) in ledger.PRICES else MODEL,
                             resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal":
        ledger.add_step(con, project_id, stage, "failed", detail="model refused")
        return None, usd
    return json.loads(next(b.text for b in resp.content if b.type == "text")), usd


def _normalize_seconds(data, rate):
    for s in data["sections"]:
        s["seconds"] = max(1, round(len(s["narration"]) / rate))
    return data


def write_script(con, client, project_id, target_seconds=480, max_fixes=2):
    """Writes the script, then re-prompts (up to `max_fixes` times) while its spoken length misses the target by > tolerance."""
    p = con.execute("SELECT brief_json FROM projects WHERE project_id=?", (project_id,)).fetchone()
    brief = json.loads(p["brief_json"])
    rate = CHARS_PER_SEC.get(brief.get("lang"), 6.5)
    target = int(target_seconds * rate)
    data, total = _call(con, client, project_id, "script", SYSTEM,
                        {"brief": brief, "target_seconds": target_seconds, "target_narration_chars": target, "chars_per_second": rate})
    if data is None:
        return None
    fixes = 0
    while fixes < max_fixes and abs(narration_chars(data) - target) / target > LENGTH_TOLERANCE:
        n = narration_chars(data)
        verb = "EXPAND (add substance, examples, concrete detail; no padding)" if n < target else "TRIM (cut repetition, keep the best material)"
        fixed, usd = _call(con, client, project_id, "script_fix", REVISE_SYSTEM, {
            "instruction": f"The narration is {n} characters but the target is {target} (+-10%). {verb}. Keep the original angle, hook and section structure.",
            "target_narration_chars": target, "chars_per_second": rate, "script": data})
        total += usd
        if fixed is None:
            break
        data, fixes = fixed, fixes + 1
    _normalize_seconds(data, rate)
    ledger.add_step(con, project_id, "script", "done", data,
                    detail=f"cost_usd={total:.4f} narration_chars={narration_chars(data)} target={target} fixes={fixes}")
    con.execute("UPDATE projects SET status='script', title=? WHERE project_id=?", (data["title_options"][0], project_id))
    con.commit()
    return data


def revise_with_feedback(con, client, project_id, data, issues, unverified_claims, lang="ja"):
    """Applies QA feedback: removes or softens claims that cannot be verified, keeps the length."""
    rate = CHARS_PER_SEC.get(lang, 6.5)
    n = narration_chars(data)
    revised, _ = _call(con, client, project_id, "script_revise", REVISE_SYSTEM, {
        "instruction": ("Fix the reviewer's issues. For every unverified claim: remove it, or rewrite it as a clearly hedged general statement "
                        "without invented numbers, studies or quotes; never keep a precise statistic you cannot source. List what remains "
                        "in fact_claims_to_verify. Keep total narration length within 10% of the current length."),
        "issues": issues, "unverified_claims": unverified_claims, "current_narration_chars": n, "chars_per_second": rate, "script": data})
    if revised is None:
        return data
    _normalize_seconds(revised, rate)
    ledger.add_step(con, project_id, "script", "done", revised, detail="revised after QA feedback")
    return revised
