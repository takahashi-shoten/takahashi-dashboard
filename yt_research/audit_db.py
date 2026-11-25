"""Audit of the research DB (data/ytr.sqlite from the `ytr-data` branch): what it can and cannot answer. Read-only; prints a JSON report.
Usage: python3 -I yt_research/audit_db.py <path/to/ytr.sqlite>"""
import json
import sqlite3
import sys
from collections import Counter

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
q = lambda sql, *a: con.execute(sql, a).fetchall()
one = lambda sql, *a: con.execute(sql, a).fetchone()[0]
R = {}

# 1. size and freshness
R["rows"] = {t: one(f"select count(*) from {t}") for (t,) in q("select name from sqlite_master where type='table' and name not like 'sqlite_%'")}
R["runs"] = [dict(zip(("run_id", "started_at", "status", "units_used"), r)) for r in q("select run_id,started_at,status,units_used from runs order by run_id")]
R["videos_first_seen_range"] = q("select min(first_seen_at),max(first_seen_at) from videos")[0]
R["videos_last_fetched_range"] = q("select min(last_fetched_at),max(last_fetched_at) from videos")[0]
R["published_range"] = q("select min(published_at),max(published_at) from videos")[0]
R["video_snapshot_dates"] = q("select substr(observed_at,1,10) d,count(*) from video_snapshots group by d order by d")
R["channel_snapshot_dates"] = q("select substr(observed_at,1,10) d,count(*) from channel_snapshots group by d order by d")

# 2. missingness per field (videos / channels)
def miss(table, cols):
    n = one(f"select count(*) from {table}")
    return {c: round(100 * one(f"select count(*) from {table} where {c} is null or {c}=''") / n, 1) for c in cols}
R["videos_missing_pct"] = miss("videos", ["channel_id", "title", "description", "published_at", "duration_s", "format_class", "category_id", "default_language", "default_audio_language", "tags_json", "synthetic_media", "unavailable_at"])
R["channels_missing_pct"] = miss("channels", ["title", "country", "channel_published_at", "default_language", "last_audited_at"])

# 3. duplicates / integrity
R["videos_without_channel_row"] = one("select count(*) from videos v left join channels c on c.channel_id=v.channel_id where c.channel_id is null")
R["videos_without_snapshot"] = one("select count(*) from videos v where not exists (select 1 from video_snapshots s where s.video_id=v.video_id)")
R["dup_titles_same_channel"] = one("select count(*) from (select channel_id,title,count(*) c from videos group by channel_id,title having c>1)")
R["unavailable_videos"] = one("select count(*) from videos where unavailable_at is not null")

# 4. time-series ability
R["video_snapshots_per_video"] = Counter(n for (n,) in q("select count(*) from video_snapshots group by video_id")).most_common(6)
R["channel_snapshots_per_channel"] = Counter(n for (n,) in q("select count(*) from channel_snapshots group by channel_id")).most_common(6)
R["channels_with_ge2_snapshots"] = one("select count(*) from (select channel_id from channel_snapshots group by channel_id having count(*)>=2)")
R["subscribers_at_publication_available"] = "NO: only snapshots observed on collection dates exist; subscriber count at the video's publication date is not stored"

# 5. composition and bias
R["format_class"] = q("select format_class,count(*) from videos group by 1 order by 2 desc")
R["videos_by_published_year"] = q("select substr(published_at,1,4),count(*) from videos group by 1 order by 1")
R["videos_by_lang"] = q("select coalesce(default_audio_language,default_language,'(none)'),count(*) from videos group by 1 order by 2 desc limit 12")
R["channels_by_country"] = q("select coalesce(country,'(none)'),count(*) from channels group by 1 order by 2 desc limit 12")
R["channels_by_genre"] = q("select genre,count(*),sum(audited) from channel_metrics group by 1 order by 2 desc")
R["topics_by_genre_lang"] = q("select genre,lang,count(*) from topics group by 1,2 order by 3 desc limit 25")
R["search_modes"] = q("select mode,count(*),sum(result_count),sum(new_videos),sum(hits) from search_runs group by 1")
R["discovery_times_seen"] = q("select times_seen,count(*) from discoveries group by 1 order by 1 limit 8")
R["channels_audited"] = one("select count(*) from channels where last_audited_at is not null")
R["channel_metrics_flags"] = dict(zip(("is_new", "is_small", "replicable", "declared_synthetic", "subs_hidden"), q("select sum(is_new),sum(is_small),sum(replicable),sum(declared_synthetic),sum(subs_hidden) from channel_metrics")[0]))
R["subscribers_quantiles"] = q("select min(subscribers),max(subscribers) from channel_metrics where subs_hidden=0")[0]
R["seed_cases"] = q("select video_id,label,reported_views,verification from seed_cases")
R["hypotheses_by_status"] = q("select genre,status,count(*) from hypotheses group by 1,2 order by 1,2")
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
