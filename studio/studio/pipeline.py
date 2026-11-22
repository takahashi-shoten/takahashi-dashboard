"""Stage registry with honest status. Only brief + script are implemented; the rest report not_connected."""
from . import ledger

STAGES = [
    ("brief", "done-when: research brief stored"),
    ("script", "Claude API (needs ANTHROPIC_API_KEY)"),
    ("voice", "text-to-speech provider: NOT connected"),
    ("visuals", "image/video generation provider: NOT connected"),
    ("edit", "assembly/editing (ffmpeg): NOT built"),
    ("qa", "fact check + policy check: NOT built"),
    ("approval", "owner approval gate (publish is never automatic)"),
]


def status(con, project_id):
    out = []
    for stage, note in STAGES:
        r = con.execute("SELECT status FROM steps WHERE project_id=? AND stage=? ORDER BY id DESC LIMIT 1", (project_id, stage)).fetchone()
        s = r["status"] if r else ("pending" if stage in ("brief", "script", "approval") else "not_connected")
        out.append((stage, s, note))
    return out


def approve_publish(con, project_id, owner):
    """Records the owner's approval. Nothing here publishes; a later stage must check this row."""
    con.execute("INSERT INTO approvals(project_id,action,approved_by,approved_at) VALUES(?,?,?,?)",
                (project_id, "publish", owner, ledger.now()))
    con.commit()


def is_publish_approved(con, project_id):
    return con.execute("SELECT 1 FROM approvals WHERE project_id=? AND action='publish'", (project_id,)).fetchone() is not None
