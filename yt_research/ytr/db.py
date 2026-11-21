"""SQLite storage.

Static attributes live in `videos` / `channels` (one row per ID, upserted).
Changing metrics live in `*_snapshots` keyed by (id, observed_at), so repeated
collection never duplicates an entity but keeps the full time series.
"""
import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS runs(
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT,
  status TEXT, units_used INTEGER DEFAULT 0, summary_json TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS api_calls(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, quota_day TEXT, endpoint TEXT,
  units INTEGER, http_status INTEGER, error TEXT, run_id INTEGER);
CREATE TABLE IF NOT EXISTS errors(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, run_id INTEGER, stage TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS channels(
  channel_id TEXT PRIMARY KEY, title TEXT, custom_url TEXT, country TEXT,
  channel_published_at TEXT, uploads_playlist_id TEXT, default_language TEXT,
  first_seen_at TEXT, last_fetched_at TEXT, last_audited_at TEXT, audit_through TEXT);
CREATE TABLE IF NOT EXISTS channel_snapshots(
  channel_id TEXT, observed_at TEXT, subscriber_count INTEGER, subscribers_hidden INTEGER,
  video_count INTEGER, view_count INTEGER, PRIMARY KEY(channel_id, observed_at));
CREATE TABLE IF NOT EXISTS videos(
  video_id TEXT PRIMARY KEY, channel_id TEXT, title TEXT, description TEXT,
  published_at TEXT, duration_s INTEGER, format_class TEXT, category_id TEXT,
  default_language TEXT, default_audio_language TEXT, tags_json TEXT,
  live_broadcast TEXT, made_for_kids INTEGER, synthetic_media INTEGER,
  topic_categories_json TEXT, first_seen_at TEXT, last_fetched_at TEXT, unavailable_at TEXT);
CREATE TABLE IF NOT EXISTS video_snapshots(
  video_id TEXT, observed_at TEXT, view_count INTEGER, like_count INTEGER,
  comment_count INTEGER, PRIMARY KEY(video_id, observed_at));
CREATE TABLE IF NOT EXISTS topics(
  topic_id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, lang TEXT, region TEXT,
  genre TEXT, source TEXT, status TEXT DEFAULT 'active', created_at TEXT,
  runs INTEGER DEFAULT 0, last_run_at TEXT, yield_score REAL, notes TEXT,
  UNIQUE(query, lang, region));
CREATE TABLE IF NOT EXISTS search_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, topic_id INTEGER, executed_at TEXT,
  published_after TEXT, result_count INTEGER, new_videos INTEGER, duplicate_videos INTEGER,
  new_channels INTEGER, hits INTEGER, music_excluded INTEGER);
CREATE TABLE IF NOT EXISTS discoveries(
  video_id TEXT, topic_id INTEGER, first_run_id INTEGER, first_rank INTEGER, times_seen INTEGER DEFAULT 1,
  PRIMARY KEY(video_id, topic_id));
CREATE TABLE IF NOT EXISTS hypotheses(
  hyp_id TEXT PRIMARY KEY, genre TEXT, statement TEXT, test_json TEXT, source TEXT,
  status TEXT, evidence_json TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS hypothesis_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, hyp_id TEXT, ts TEXT, old_status TEXT, new_status TEXT, evidence_json TEXT);
CREATE TABLE IF NOT EXISTS seed_cases(
  video_id TEXT PRIMARY KEY, label TEXT, reported_views TEXT, verified_at TEXT, verification TEXT);
CREATE TABLE IF NOT EXISTS date_samples(
  video_id TEXT, topic_id INTEGER, first_run_id INTEGER, sampled_at TEXT, PRIMARY KEY(video_id, topic_id));
CREATE INDEX IF NOT EXISTS ix_videos_channel ON videos(channel_id);
CREATE INDEX IF NOT EXISTS ix_videos_pub ON videos(published_at);
CREATE INDEX IF NOT EXISTS ix_api_day ON api_calls(quota_day);
"""

LATEST_VIDEO_VIEW = """
CREATE TEMP VIEW IF NOT EXISTS v_latest AS
SELECT v.*, s.view_count, s.like_count, s.comment_count, s.observed_at
FROM videos v JOIN video_snapshots s ON s.video_id = v.video_id
WHERE s.observed_at = (SELECT MAX(observed_at) FROM video_snapshots WHERE video_id = v.video_id);
CREATE TEMP VIEW IF NOT EXISTS c_latest AS
SELECT c.*, s.subscriber_count, s.subscribers_hidden, s.video_count, s.view_count AS channel_views, s.observed_at
FROM channels c LEFT JOIN channel_snapshots s ON s.channel_id = c.channel_id
 AND s.observed_at = (SELECT MAX(observed_at) FROM channel_snapshots WHERE channel_id = c.channel_id);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    from .analyze import CHANNEL_METRICS_CREATE
    con.executescript(CHANNEL_METRICS_CREATE)
    con.executescript(LATEST_VIDEO_VIEW)
    return con


MIGRATIONS = [
    ("topics", "date_sampled_at", "TEXT"),
    ("search_runs", "mode", "TEXT DEFAULT 'top'"),
]


def _migrate(con):
    """Additive column migrations so existing databases keep working."""
    for table, col, decl in MIGRATIONS:
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    con.commit()


def log_error(con, run_id, stage, detail):
    from .util import iso, utcnow
    con.execute("INSERT INTO errors(ts, run_id, stage, detail) VALUES(?,?,?,?)",
                (iso(utcnow()), run_id, stage, str(detail)[:2000]))
    con.commit()


def upsert_video(con, item: dict, observed_at: str) -> bool:
    """Insert/refresh a video from a videos.list item. Returns True if new."""
    from .util import parse_duration, format_class
    vid = item["id"]
    sn, cd = item.get("snippet", {}), item.get("contentDetails", {})
    st, stats = item.get("status", {}), item.get("statistics", {})
    dur = parse_duration(cd.get("duration"))
    existed = con.execute("SELECT 1 FROM videos WHERE video_id=?", (vid,)).fetchone() is not None
    synth = st.get("containsSyntheticMedia")
    row = dict(
        video_id=vid, channel_id=sn.get("channelId"), title=sn.get("title"),
        description=(sn.get("description") or "")[:400], published_at=sn.get("publishedAt"),
        duration_s=dur, format_class=format_class(dur), category_id=sn.get("categoryId"),
        default_language=sn.get("defaultLanguage"), default_audio_language=sn.get("defaultAudioLanguage"),
        tags_json=json.dumps(sn.get("tags", []), ensure_ascii=False),
        live_broadcast=sn.get("liveBroadcastContent"),
        made_for_kids=None if "madeForKids" not in st else int(st["madeForKids"]),
        synthetic_media=None if synth is None else int(synth),
        topic_categories_json=json.dumps(item.get("topicDetails", {}).get("topicCategories", [])),
        last_fetched_at=observed_at,
    )
    if existed:
        sets = ", ".join(f"{k}=:{k}" for k in row if k != "video_id")
        con.execute(f"UPDATE videos SET {sets} WHERE video_id=:video_id", row)
    else:
        row["first_seen_at"] = observed_at
        cols = ", ".join(row)
        con.execute(f"INSERT INTO videos({cols}) VALUES({', '.join(':' + k for k in row)})", row)
    if "viewCount" in stats:
        con.execute(
            "INSERT OR REPLACE INTO video_snapshots VALUES(?,?,?,?,?)",
            (vid, observed_at, int(stats["viewCount"]),
             int(stats["likeCount"]) if "likeCount" in stats else None,
             int(stats["commentCount"]) if "commentCount" in stats else None))
    return not existed


def upsert_channel(con, item: dict, observed_at: str) -> bool:
    cid = item["id"]
    sn, stats = item.get("snippet", {}), item.get("statistics", {})
    uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    existed = con.execute("SELECT 1 FROM channels WHERE channel_id=?", (cid,)).fetchone() is not None
    row = dict(channel_id=cid, title=sn.get("title"), custom_url=sn.get("customUrl"),
               country=sn.get("country"), channel_published_at=sn.get("publishedAt"),
               uploads_playlist_id=uploads, default_language=sn.get("defaultLanguage"),
               last_fetched_at=observed_at)
    if existed:
        sets = ", ".join(f"{k}=:{k}" for k in row if k != "channel_id")
        con.execute(f"UPDATE channels SET {sets} WHERE channel_id=:channel_id", row)
    else:
        row["first_seen_at"] = observed_at
        con.execute(f"INSERT INTO channels({', '.join(row)}) VALUES({', '.join(':' + k for k in row)})", row)
    hidden = bool(stats.get("hiddenSubscriberCount"))
    con.execute("INSERT OR REPLACE INTO channel_snapshots VALUES(?,?,?,?,?,?)",
                (cid, observed_at,
                 None if hidden or "subscriberCount" not in stats else int(stats["subscriberCount"]),
                 int(hidden),
                 int(stats["videoCount"]) if "videoCount" in stats else None,
                 int(stats["viewCount"]) if "viewCount" in stats else None))
    return not existed
