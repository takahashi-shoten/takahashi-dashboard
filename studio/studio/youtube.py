"""YouTube publishing + measurement over raw REST (`requests`, no Google SDK).

Safety: uploads default to 'private'; 'public' is refused unless the ledger holds a
'publish_public' approval for the project. Credentials come only from env vars and are never
logged or placed in exception messages. OAuth (upload/private reads/analytics) is kept separate
from any API key (public reads only; not used here).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import ledger
from .errors import NotConnected

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"

CORE_METRICS = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
                "subscribersGained", "subscribersLost"]
# New (2026) names first, then older names (may be channel-level only / 400). Each tried separately.
IMPRESSION_METRICS = ["videoThumbnailImpressions", "videoThumbnailImpressionsClickRate",
                      "impressions", "impressionsClickThroughRate"]
REVENUE_METRICS = ["estimatedRevenue"]  # needs yt-analytics-monetary.readonly
TRAFFIC_DIMENSION = "insightTrafficSourceType"
COUNTRY_DIMENSION = "country"

PRIVACY = ("private", "unlisted", "public")
CHECKPOINTS = (("24h", 24), ("72h", 72), ("7d", 168), ("28d", 672))
APPROVE_PUBLIC = "publish_public"

METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS video_metrics(
  video_id TEXT, project_id INTEGER, observed_at TEXT, age_hours REAL, metric TEXT, value REAL,
  dimension TEXT, dimension_value TEXT);
"""


class YouTubeError(RuntimeError):
    pass


class ApprovalRequired(YouTubeError):
    pass


class MetricUnavailable(YouTubeError):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


def _err(r, what):
    try:
        msg = r.json().get("error", {})
        msg = msg.get("message", "") if isinstance(msg, dict) else str(msg)
    except (ValueError, AttributeError):
        msg = ""
    return YouTubeError(f"{what}: HTTP {r.status_code}: {str(msg)[:300]}")


# ---------------------------------------------------------------- auth
def access_token(session=None, timeout=30) -> str:
    env = {k: os.environ.get(k, "").strip()
           for k in ("YT_OAUTH_CLIENT_ID", "YT_OAUTH_CLIENT_SECRET", "YT_OAUTH_REFRESH_TOKEN")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise NotConnected("set " + ", ".join(missing) + " (YouTube OAuth2 refresh-token flow)")
    r = (session or requests).post(TOKEN_URL, timeout=timeout, data={
        "client_id": env["YT_OAUTH_CLIENT_ID"], "client_secret": env["YT_OAUTH_CLIENT_SECRET"],
        "refresh_token": env["YT_OAUTH_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        try:
            code = str(r.json().get("error", ""))[:60]  # e.g. invalid_grant; never the description/body
        except (ValueError, AttributeError):
            code = ""
        raise YouTubeError(f"token exchange failed: HTTP {r.status_code} {code}".strip())
    tok = r.json().get("access_token")
    if not tok:
        raise YouTubeError("token exchange returned no access_token")
    return tok


def _auth(session):
    return {"Authorization": "Bearer " + access_token(session)}


# ---------------------------------------------------------------- approvals
def approve(con, project_id, action, by):
    con.execute("INSERT INTO approvals(project_id,action,approved_by,approved_at) VALUES(?,?,?,?)",
                (project_id, action, by, ledger.now()))
    con.commit()


def is_approved(con, project_id, action) -> bool:
    if con is None or project_id is None:
        return False
    return con.execute("SELECT 1 FROM approvals WHERE project_id=? AND action=? LIMIT 1",
                       (project_id, action)).fetchone() is not None


def _gate(privacy, con, project_id):
    if privacy not in PRIVACY:
        raise YouTubeError(f"privacy must be one of {PRIVACY}")
    if privacy == "public" and not is_approved(con, project_id, APPROVE_PUBLIC):
        raise ApprovalRequired(f"public publishing refused: no '{APPROVE_PUBLIC}' approval recorded "
                               f"for project {project_id}")


# ---------------------------------------------------------------- upload
def upload_video(path, title, description="", tags=None, privacy="private", category_id="22",
                 made_for_kids=False, synthetic_media=True, default_language=None,
                 session=None, con=None, project_id=None, timeout=600) -> str:
    _gate(privacy, con, project_id)
    data = Path(path).read_bytes()
    snippet = {"title": title, "description": description, "tags": list(tags or []), "categoryId": str(category_id)}
    if default_language:
        snippet["defaultLanguage"] = default_language
    body = {"snippet": snippet, "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(made_for_kids),
                                           "containsSyntheticMedia": bool(synthetic_media)}}
    s = session or requests
    hdr = _auth(session)
    r = s.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"}, timeout=60,
               data=json.dumps(body), headers={**hdr, "Content-Type": "application/json; charset=UTF-8",
                                               "X-Upload-Content-Length": str(len(data)),
                                               "X-Upload-Content-Type": "video/*"})
    if r.status_code != 200:
        raise _err(r, "upload init")
    loc = r.headers.get("Location")
    if not loc:
        raise YouTubeError("upload init returned no resumable session URL")
    r = s.put(loc, data=data, timeout=timeout, headers={**hdr, "Content-Type": "video/*"})
    if r.status_code not in (200, 201):
        raise _err(r, "upload")
    vid = r.json().get("id")
    if not vid:
        raise YouTubeError("upload response had no video id")
    actual = (r.json().get("status") or {}).get("privacyStatus")  # what YouTube really set
    if con is not None and project_id is not None:
        ledger.add_step(con, project_id, "youtube_upload", "done",
                        {"video_id": vid, "privacy": actual or privacy, "requested_privacy": privacy,
                         "uploaded_at": ledger.now()})
    return vid


def set_privacy(video_id, privacy, con, project_id, session=None, timeout=60):
    _gate(privacy, con, project_id)
    s = session or requests
    r = s.put(f"{API}/videos", params={"part": "status"}, timeout=timeout,
              headers={**_auth(session), "Content-Type": "application/json"},
              data=json.dumps({"id": video_id, "status": {"privacyStatus": privacy}}))
    if r.status_code != 200:
        raise _err(r, "set_privacy")
    if con is not None and project_id is not None:
        ledger.add_step(con, project_id, "youtube_privacy", "done",
                        {"video_id": video_id, "privacy": privacy, "at": ledger.now()})
    return r.json()


# ---------------------------------------------------------------- measurement
def _get(url, params, session, what, timeout=60):
    r = (session or requests).get(url, params=params, headers=_auth(session), timeout=timeout)
    if r.status_code != 200:
        raise _err(r, what)
    return r.json()


def channel_info(session=None):
    return _get(f"{API}/channels", {"part": "snippet,statistics", "mine": "true"}, session, "channel_info")


def video_stats(ids, session=None):
    ids = list(ids)
    out = {}
    for i in range(0, len(ids), 50):
        j = _get(f"{API}/videos", {"part": "statistics,status", "id": ",".join(ids[i:i + 50])}, session, "video_stats")
        for it in j.get("items", []):
            out[it["id"]] = {"statistics": it.get("statistics", {}),
                             "privacyStatus": (it.get("status") or {}).get("privacyStatus")}
    return out


def _report(video_ids, start, end, metrics, dimensions, session, sort=None, max_results=None):
    params = {"ids": "channel==MINE", "startDate": start, "endDate": end, "metrics": ",".join(metrics)}
    if video_ids:
        params["filters"] = "video==" + ",".join(video_ids)
    if dimensions:
        params["dimensions"] = ",".join(dimensions)
    if sort:
        params["sort"] = sort
    if max_results:
        params["maxResults"] = max_results
    r = (session or requests).get(ANALYTICS_URL, params=params, headers=_auth(session), timeout=60)
    if r.status_code in (400, 403):
        raise MetricUnavailable(r.status_code)
    if r.status_code != 200:
        raise _err(r, "analytics")
    return r.json()


def analytics_report(video_ids, start, end, metrics=None, dimensions=None, session=None, sort=None, max_results=None):
    """Query metrics; on 400/403 find which metrics are unavailable, drop them, and report them.

    Returns {"columnHeaders", "rows", "metrics", "unavailable_metrics"}.
    """
    metrics = list(metrics or CORE_METRICS)
    try:
        j = _report(video_ids, start, end, metrics, dimensions, session, sort, max_results)
        return {"columnHeaders": j.get("columnHeaders", []), "rows": j.get("rows", []), "metrics": metrics,
                "unavailable_metrics": []}
    except MetricUnavailable:
        pass
    ok, bad = [], []
    for m in metrics:
        try:
            _report(video_ids, start, end, [m], dimensions, session, None, 1)
            ok.append(m)
        except MetricUnavailable:
            bad.append(m)
    if not ok:
        return {"columnHeaders": [], "rows": [], "metrics": [], "unavailable_metrics": bad}
    j = _report(video_ids, start, end, ok, dimensions, session, sort, max_results)
    return {"columnHeaders": j.get("columnHeaders", []), "rows": j.get("rows", []), "metrics": ok,
            "unavailable_metrics": bad}


# ---------------------------------------------------------------- storage
def _dt(x):
    d = x if isinstance(x, datetime) else datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_schema(con):
    con.executescript(METRICS_SCHEMA)


def _store(con, project_id, video_id, observed, age, metric, value, dim=None, dimval=None):
    con.execute("INSERT INTO video_metrics VALUES(?,?,?,?,?,?,?,?)",
                (video_id, project_id, observed, age, metric, value, dim, dimval))


def due_checkpoints(published_at, now=None, con=None, video_id=None):
    """Checkpoint labels (24h/72h/7d/28d) whose age has elapsed and (if con given) not yet stored."""
    age = (_dt(now or datetime.now(timezone.utc)) - _dt(published_at)).total_seconds() / 3600
    done = set()
    if con is not None and video_id is not None:
        ensure_schema(con)
        done = {r[0] for r in con.execute(
            "SELECT dimension_value FROM video_metrics WHERE video_id=? AND metric='checkpoint'", (video_id,))}
    return [lbl for lbl, h in CHECKPOINTS if age >= h and lbl not in done]


def snapshot(con, project_id, video_id, published_at, session=None, now=None, checkpoint=None):
    """Fetch stats + analytics and store them. Returns {"stored", "age_hours", "unavailable_metrics"}."""
    ensure_schema(con)
    now_d = _dt(now or datetime.now(timezone.utc))
    pub = _dt(published_at)
    age = round((now_d - pub).total_seconds() / 3600, 2)
    obs = _iso(now_d)
    start, end = pub.date().isoformat(), max(now_d.date(), pub.date()).isoformat()
    n, unavailable = 0, []

    st = video_stats([video_id], session).get(video_id, {})
    for k, v in (st.get("statistics") or {}).items():
        try:
            _store(con, project_id, video_id, obs, age, "data_api." + k, float(v))
            n += 1
        except (TypeError, ValueError):
            pass

    def run(metrics, dims=None):
        nonlocal n
        rep = analytics_report([video_id], start, end, metrics, dims, session)
        unavailable.extend(m for m in rep["unavailable_metrics"] if m not in unavailable)
        names = [h["name"] for h in rep["columnHeaders"]]
        nd = len(dims or [])
        for row in rep["rows"]:
            dv = ",".join(str(x) for x in row[:nd]) or None
            for name, val in zip(names[nd:], row[nd:]):
                _store(con, project_id, video_id, obs, age, name, val, dims[0] if dims else None, dv)
                n += 1

    run(CORE_METRICS)
    for m in IMPRESSION_METRICS:  # separate attempts
        run([m])
    run(["views", "estimatedMinutesWatched"], [TRAFFIC_DIMENSION])
    run(["views", "estimatedMinutesWatched"], [COUNTRY_DIMENSION])
    for m in REVENUE_METRICS:
        run([m])
    if checkpoint:
        _store(con, project_id, video_id, obs, age, "checkpoint", age, "checkpoint", checkpoint)
    con.commit()
    return {"stored": n, "age_hours": age, "unavailable_metrics": unavailable}
