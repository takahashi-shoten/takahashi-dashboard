"""SQLite ledger: projects, per-step artifacts and *measured* costs (USD).

Costs come from API usage returned by the provider, never from estimates. Revenue is recorded
separately so profit per video can be computed from real numbers only.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(os.environ.get("STUDIO_DB", Path(__file__).resolve().parent.parent / "data" / "studio.sqlite"))

# USD per 1M tokens (Anthropic first-party list prices, cached 2026-11).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(
  project_id INTEGER PRIMARY KEY AUTOINCREMENT, genre TEXT, lang TEXT, platform TEXT, title TEXT,
  status TEXT, brief_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS steps(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, stage TEXT, status TEXT,
  artifact_json TEXT, detail TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS costs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, stage TEXT, provider TEXT, model TEXT,
  input_tokens INTEGER, output_tokens INTEGER, usd REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS revenue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, source TEXT, usd REAL, period TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, action TEXT, approved_by TEXT, approved_at TEXT);
"""


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path=None):
    path = path or DB
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def cost_usd(model, input_tokens, output_tokens):
    pin, pout = PRICES[model]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


def record_cost(con, project_id, stage, provider, model, input_tokens, output_tokens):
    usd = cost_usd(model, input_tokens, output_tokens)
    con.execute("INSERT INTO costs(project_id,stage,provider,model,input_tokens,output_tokens,usd,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (project_id, stage, provider, model, input_tokens, output_tokens, usd, now()))
    con.commit()
    return usd


def add_step(con, project_id, stage, status, artifact=None, detail=None):
    con.execute("INSERT INTO steps(project_id,stage,status,artifact_json,detail,created_at) VALUES(?,?,?,?,?,?)",
                (project_id, stage, status, json.dumps(artifact, ensure_ascii=False) if artifact is not None else None, detail, now()))
    con.commit()


def profit(con, project_id):
    c = con.execute("SELECT COALESCE(SUM(usd),0) FROM costs WHERE project_id=?", (project_id,)).fetchone()[0]
    r = con.execute("SELECT COALESCE(SUM(usd),0) FROM revenue WHERE project_id=?", (project_id,)).fetchone()[0]
    return dict(cost_usd=c, revenue_usd=r, profit_usd=r - c)


def record_usage(con, project_id, stage, provider, model, input_tokens, output_tokens, usd=None):
    """For providers whose price table we do not hold (usd=None stays None, never guessed)."""
    con.execute("INSERT INTO costs(project_id,stage,provider,model,input_tokens,output_tokens,usd,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (project_id, stage, provider, model, input_tokens, output_tokens, usd, now()))
    con.commit()
