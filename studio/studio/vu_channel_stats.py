"""Public numbers for every upload of one channel (YouTube Data API, measured) + thumbnails of chosen videos, to separate title / thumbnail / timing effects.
Usage: python -m studio.vu_channel_stats <seed_video_id> <id1,id2,...>   (needs YOUTUBE_API_KEY). Writes work/gemini_live/marketing/channel_stats.json and thumbs/*.jpg"""
import json
import sys

import requests

from . import vu_diag as d
from .vu_marketing import yt


def main():
    seed = sys.argv[1]
    want = [x for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else []) if x]
    ch = yt("videos", part="snippet", id=seed)["items"][0]["snippet"]["channelId"]
    chinfo = yt("channels", part="snippet,statistics", id=ch)["items"][0]
    uploads = "UU" + ch[2:]
    ids, tok = [], None
    while True:
        r = yt("playlistItems", part="snippet", playlistId=uploads, maxResults=50, **({"pageToken": tok} if tok else {}))
        ids += [i["snippet"]["resourceId"]["videoId"] for i in r.get("items", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    rows = []
    for i in range(0, len(ids), 50):
        r = yt("videos", part="snippet,contentDetails,statistics", id=",".join(ids[i:i + 50]))
        for it in r.get("items", []):
            st = it["statistics"]
            rows.append(dict(id=it["id"], title=it["snippet"]["title"], published=it["snippet"]["publishedAt"], duration=it["contentDetails"]["duration"],
                             views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)) if "likeCount" in st else None,
                             comments=int(st.get("commentCount", 0)) if "commentCount" in st else None, live=it["snippet"].get("liveBroadcastContent")))
    out = d.OUT.parent / "marketing"
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    thumbs = {}
    for v in want:
        for q in ("maxresdefault", "hqdefault"):
            rr = requests.get(f"https://i.ytimg.com/vi/{v}/{q}.jpg", timeout=30)
            if rr.status_code == 200 and len(rr.content) > 2000:
                (out / "thumbs" / f"{v}.jpg").write_bytes(rr.content)
                thumbs[v] = q
                break
    doc = dict(fetched_at=d.now(), channel=dict(id=ch, title=chinfo["snippet"]["title"], subs=chinfo["statistics"].get("subscriberCount"), video_count=chinfo["statistics"].get("videoCount"),
                                               total_views=chinfo["statistics"].get("viewCount")), uploads_listed=len(ids), videos=rows, thumbs=thumbs)
    (out / "channel_stats.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print("STATS videos", len(rows), "| thumbs", thumbs, "| channel", doc["channel"])


if __name__ == "__main__":
    main()
