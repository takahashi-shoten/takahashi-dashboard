"""One research cycle: refresh -> search -> hydrate -> channel audit.

Each stage is isolated: an error is logged and the cycle continues; quota exhaustion
stops spending cleanly and the next scheduled run resumes from the DB state.
"""
from . import config, topics
from .api import YouTubeClient, QuotaExceeded, BudgetExhausted, ApiError
from .db import upsert_video, upsert_channel, log_error
from .util import iso, utcnow, window_start


class Cycle:
    def __init__(self, con, client: YouTubeClient, run_id):
        self.con, self.yt, self.run_id = con, client, run_id
        self.stats = dict(searches=0, search_results=0, new_videos=0, duplicate_videos=0,
                          new_channels=0, channels_audited=0, audit_videos=0, refreshed=0,
                          music_excluded=0, errors=0, stopped_by=None)

    def _err(self, stage, e):
        self.stats["errors"] += 1
        log_error(self.con, self.run_id, stage, repr(e))

    # -- stage helpers ---------------------------------------------------------
    def hydrate(self, ids):
        """videos.list for ids; returns {video_id: is_new}. Missing ids marked unavailable."""
        now = iso(utcnow())
        items = self.yt.videos(list(ids))
        got = {}
        for it in items:
            got[it["id"]] = upsert_video(self.con, it, now)
        for vid in set(ids) - set(got):
            self.con.execute("UPDATE videos SET unavailable_at=? WHERE video_id=? AND unavailable_at IS NULL", (now, vid))
        self.con.commit()
        return got

    def ensure_channels(self, channel_ids, refresh=False):
        now = iso(utcnow())
        if not refresh:
            known = {r[0] for r in self.con.execute(
                f"SELECT channel_id FROM channels WHERE channel_id IN ({','.join('?' * len(channel_ids))})",
                list(channel_ids))} if channel_ids else set()
            channel_ids = [c for c in channel_ids if c not in known]
        new = 0
        for it in self.yt.channels(list(channel_ids)):
            new += upsert_channel(self.con, it, now)
        self.con.commit()
        self.stats["new_channels"] += new
        return new

    # -- stages ----------------------------------------------------------------
    def refresh_tracked(self):
        """New view snapshot for videos inside the window that are hits or near-hits."""
        since = iso(window_start(config.WINDOW_DAYS + 30))
        ids = [r[0] for r in self.con.execute("""
            SELECT video_id FROM v_latest WHERE published_at >= ? AND view_count >= ? AND unavailable_at IS NULL
              AND observed_at < ? ORDER BY view_count DESC LIMIT ?""",
            (since, config.MIN_VIEWS // 5, iso(window_start(0.9)), config.REFRESH_MAX_VIDEOS))]
        if ids:
            self.hydrate(ids)
            self.stats["refreshed"] += len(ids)

    def search_topic(self, t):
        published_after = iso(window_start(config.WINDOW_DAYS))
        ids = self.yt.search_videos(t["query"], published_after, lang=t["lang"], region=t["region"])
        self.stats["searches"] += 1
        self.stats["search_results"] += len(ids)
        known = {r[0] for r in self.con.execute(
            f"SELECT video_id FROM videos WHERE video_id IN ({','.join('?' * len(ids))})", ids)} if ids else set()
        for rank, vid in enumerate(ids):
            self.con.execute("""INSERT INTO discoveries(video_id, topic_id, first_run_id, first_rank) VALUES(?,?,?,?)
                ON CONFLICT(video_id, topic_id) DO UPDATE SET times_seen=times_seen+1""",
                             (vid, t["topic_id"], self.run_id, rank))
        new_ids = [v for v in ids if v not in known]
        if new_ids:
            self.hydrate(new_ids)
        rows = self.con.execute(
            f"SELECT video_id, channel_id, category_id, view_count, published_at FROM v_latest WHERE video_id IN ({','.join('?' * len(ids))})",
            ids).fetchall() if ids else []
        music = sum(1 for r in rows if r["category_id"] == config.MUSIC_CATEGORY_ID)
        hits = [r for r in rows if r["category_id"] != config.MUSIC_CATEGORY_ID
                and (r["view_count"] or 0) >= config.MIN_VIEWS and r["published_at"] >= published_after]
        hit_channels = sorted({r["channel_id"] for r in hits})
        before = {r[0] for r in self.con.execute(
            f"SELECT channel_id FROM channels WHERE channel_id IN ({','.join('?' * len(hit_channels))})",
            hit_channels)} if hit_channels else set()
        if hits:
            self.ensure_channels(sorted({r["channel_id"] for r in rows}))
        new_hit_channels = len(set(hit_channels) - before)
        now = iso(utcnow())
        self.con.execute("""INSERT INTO search_runs(run_id, topic_id, executed_at, published_after, result_count,
            new_videos, duplicate_videos, new_channels, hits, music_excluded) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                         (self.run_id, t["topic_id"], now, published_after, len(ids), len(new_ids),
                          len(ids) - len(new_ids), new_hit_channels, len(hits), music))
        topics.update_yield(self.con, t["topic_id"], new_hit_channels,
                            len([h for h in hits if h["video_id"] in new_ids]), len(ids), now)
        self.con.commit()
        self.stats["new_videos"] += len(new_ids)
        self.stats["duplicate_videos"] += len(ids) - len(new_ids)
        self.stats["music_excluded"] += music

    def channels_to_audit(self):
        """Channels with >=1 non-music hit in the window, not audited recently. Small/new first."""
        since = iso(window_start(config.WINDOW_DAYS))
        stale = iso(window_start(config.CHANNEL_REAUDIT_DAYS))
        return self.con.execute("""
          SELECT c.channel_id, c.uploads_playlist_id FROM c_latest c
          WHERE c.uploads_playlist_id IS NOT NULL AND (c.last_audited_at IS NULL OR c.last_audited_at < ?)
            AND EXISTS(SELECT 1 FROM v_latest v WHERE v.channel_id=c.channel_id AND v.published_at>=?
                       AND v.view_count>=? AND v.category_id!='10')
          ORDER BY (c.last_audited_at IS NOT NULL), COALESCE(c.subscriber_count, 0) ASC""",
                                (stale, since, config.MIN_VIEWS)).fetchall()

    def audit_channel(self, ch):
        since = iso(window_start(config.WINDOW_DAYS))
        ids, covered_from = self.yt.playlist_video_ids(ch["uploads_playlist_id"], since, config.CHANNEL_AUDIT_MAX_PAGES)
        if ids:
            self.hydrate(ids)
        self.ensure_channels([ch["channel_id"]], refresh=True)
        self.con.execute("UPDATE channels SET last_audited_at=?, audit_through=? WHERE channel_id=?",
                         (iso(utcnow()), covered_from, ch["channel_id"]))
        self.con.commit()
        self.stats["channels_audited"] += 1
        self.stats["audit_videos"] += len(ids)

    # -- driver ----------------------------------------------------------------
    def run(self, searches=config.SEARCHES_PER_RUN, audit_reserve=1500):
        stages = [("refresh", self.refresh_tracked)]
        for stage, fn in stages:
            try:
                fn()
            except (QuotaExceeded, BudgetExhausted) as e:
                self.stats["stopped_by"] = f"{stage}: {e}"
                return self.stats
            except Exception as e:  # noqa: BLE001 - keep cycle alive
                self._err(stage, e)
        for t in topics.select_topics(self.con, searches):
            if not self.yt.can_spend(config.COST["search"] + 4 + audit_reserve):
                break
            try:
                self.search_topic(t)
            except (QuotaExceeded, BudgetExhausted) as e:
                self.stats["stopped_by"] = f"search: {e}"
                break
            except Exception as e:  # noqa: BLE001
                self._err(f"search:{t['topic_id']}", e)
        for ch in self.channels_to_audit():
            if not self.yt.can_spend(10):
                break
            try:
                self.audit_channel(ch)
            except (QuotaExceeded, BudgetExhausted) as e:
                self.stats["stopped_by"] = f"audit: {e}"
                break
            except ApiError as e:
                self._err(f"audit:{ch['channel_id']}", e)
                # mark as audited to avoid retry storms on deleted/private playlists
                self.con.execute("UPDATE channels SET last_audited_at=? WHERE channel_id=?",
                                 (iso(utcnow()), ch["channel_id"]))
                self.con.commit()
            except Exception as e:  # noqa: BLE001
                self._err(f"audit:{ch['channel_id']}", e)
        return self.stats
