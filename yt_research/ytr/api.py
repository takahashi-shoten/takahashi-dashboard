"""YouTube Data API v3 client with quota accounting, retries and error logging."""
import os
import time

import requests

from . import config
from .util import iso, utcnow

BASE = "https://www.googleapis.com/youtube/v3/"


class QuotaExceeded(Exception):
    pass


class BudgetExhausted(Exception):
    pass


class ApiError(Exception):
    pass


def quota_day(now=None) -> str:
    from zoneinfo import ZoneInfo
    return (now or utcnow()).astimezone(ZoneInfo(config.QUOTA_TZ)).strftime("%Y-%m-%d")


class YouTubeClient:
    def __init__(self, con, run_id=None, budget=config.RUN_BUDGET, session=None, sleep=time.sleep):
        self.con, self.run_id, self.budget = con, run_id, budget
        self.spent = 0
        self.key = os.environ.get("YOUTUBE_API_KEY", "")
        self.http = session or requests.Session()
        self.sleep = sleep

    # -- quota ---------------------------------------------------------------
    def used_today(self) -> int:
        r = self.con.execute("SELECT COALESCE(SUM(units),0) FROM api_calls WHERE quota_day=?",
                             (quota_day(),)).fetchone()
        return r[0]

    def remaining_today(self) -> int:
        return config.DAILY_QUOTA - self.used_today()

    def can_spend(self, units: int) -> bool:
        return self.spent + units <= self.budget and units <= self.remaining_today()

    def _record(self, endpoint, units, status, error=None):
        self.con.execute(
            "INSERT INTO api_calls(ts, quota_day, endpoint, units, http_status, error, run_id) VALUES(?,?,?,?,?,?,?)",
            (iso(utcnow()), quota_day(), endpoint, units, status, error, self.run_id))
        self.con.commit()

    # -- transport -----------------------------------------------------------
    def get(self, endpoint: str, **params) -> dict:
        units = config.COST[endpoint]
        if not self.can_spend(units):
            raise BudgetExhausted(f"{endpoint}: run budget/daily quota reached (spent={self.spent})")
        headers = {"Accept": "application/json"}
        # Key goes in a header: works with a local env var and with proxy-injected credentials.
        headers["X-Goog-Api-Key"] = self.key or "proxy-injected"
        last = None
        for attempt in range(5):
            try:
                r = self.http.get(BASE + endpoint, params=params, headers=headers, timeout=30)
            except requests.RequestException as e:  # network failure -> retry
                last = f"network: {e}"
                self.sleep(min(2 ** attempt, 30))
                continue
            # Every request that reaches the API costs quota, even failures.
            if r.status_code == 200:
                self.spent += units
                self._record(endpoint, units, 200)
                return r.json()
            try:
                err = r.json().get("error", {})
            except ValueError:
                err = {"message": r.text[:300]}
            reasons = {e.get("reason") for e in err.get("errors", [])}
            msg = f"{r.status_code} {err.get('message', '')} {sorted(x for x in reasons if x)}"
            self.spent += units
            self._record(endpoint, units, r.status_code, msg[:500])
            if reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"} and r.status_code == 403:
                raise QuotaExceeded(msg)
            if r.status_code in (429, 500, 502, 503, 504):
                last = msg
                self.sleep(min(2 ** attempt * 2, 60))
                continue
            raise ApiError(msg)
        raise ApiError(f"gave up after retries: {last}")

    # -- endpoints -----------------------------------------------------------
    def search_videos(self, q, published_after, lang=None, region=None, order="viewCount", max_results=50,
                      published_before=None):
        p = dict(part="id", type="video", q=q, publishedAfter=published_after, order=order,
                 maxResults=max_results, safeSearch="none")
        if published_before:
            p["publishedBefore"] = published_before
        if lang:
            p["relevanceLanguage"] = lang
        if region:
            p["regionCode"] = region
        data = self.get("search", **p)
        return [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]

    def videos(self, ids):
        out = []
        for i in range(0, len(ids), 50):
            data = self.get("videos", part="snippet,contentDetails,statistics,status,topicDetails",
                            id=",".join(ids[i:i + 50]), maxResults=50)
            out += data.get("items", [])
        return out

    def channels(self, ids):
        out = []
        for i in range(0, len(ids), 50):
            data = self.get("channels", part="snippet,statistics,contentDetails",
                            id=",".join(ids[i:i + 50]), maxResults=50)
            out += data.get("items", [])
        return out

    def playlist_video_ids(self, playlist_id, since_iso, max_pages):
        """Upload playlist is newest-first; stop once items are older than `since_iso`.
        Returns (video_ids, covered_from_iso)."""
        ids, token, oldest, complete = [], None, None, False
        for _ in range(max_pages):
            p = dict(part="contentDetails", playlistId=playlist_id, maxResults=50)
            if token:
                p["pageToken"] = token
            data = self.get("playlistItems", **p)
            stop = False
            for it in data.get("items", []):
                cd = it.get("contentDetails", {})
                pub = cd.get("videoPublishedAt")
                if pub and pub < since_iso:
                    stop = True
                    continue
                if pub and (oldest is None or pub < oldest):
                    oldest = pub
                if cd.get("videoId"):
                    ids.append(cd["videoId"])
            token = data.get("nextPageToken")
            if stop or not token:
                complete = True
                break
        # complete=False: page cap hit; coverage only reaches back to `oldest`
        return ids, (since_iso if complete else (oldest or since_iso))
