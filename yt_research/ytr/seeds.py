"""Re-verify the cases reported by earlier research (third-party numbers) via the official API."""
from .db import upsert_video, upsert_channel
from .util import iso, utcnow, days_since

PAST_CASES = [
    ("kiqiQzn12rc", "The Curious Stick: Roman army camp", "4.16M-4.30M"),
    ("fRQL6LEjwFg", "GoDocs: Saudi Arabia water", "6.77M"),
    ("q2E23sEfMIo", "Paper Borders: Roman Empire", "318K"),
    ("8l-dxq3zwhs", "SimplyTold: why humans wear clothes", "324K"),
    ("BZkPquCm6v8", "Causality: world after WW3", "4.586M"),
    ("c2n4WUniQfE", "Phantom Expedition: crow language", "739K"),
    ("BQ6SjJ_VzoQ", "Vicky Qubes: bride cooking", "1.006M"),
    ("95EGhuiNAIk", "Cozy Village Tales: small rural house", "170.47M"),
    ("qT4MQLhUt2k", "Colin@NYC: helping AI short", "2.68M"),
    ("TlrjGqHhplc", "Lumz Cinema: protecting alien child", "14.1M"),
]


def verify(con, yt):
    now = iso(utcnow())
    for vid, label, rep in PAST_CASES:
        con.execute("INSERT OR IGNORE INTO seed_cases(video_id, label, reported_views) VALUES(?,?,?)", (vid, label, rep))
    items = {it["id"]: it for it in yt.videos([c[0] for c in PAST_CASES])}
    chans = {it["id"]: it for it in yt.channels(sorted({it["snippet"]["channelId"] for it in items.values()}))}
    for c in chans.values():
        upsert_channel(con, c, now)
    out = []
    for vid, label, rep in PAST_CASES:
        it = items.get(vid)
        if not it:
            res = "not_found (deleted/private or invalid ID)"
        else:
            upsert_video(con, it, now)
            sn, st = it["snippet"], it.get("statistics", {})
            ch = chans.get(sn["channelId"], {}).get("statistics", {})
            res = (f"views={int(st.get('viewCount', 0)):,} published={sn['publishedAt'][:10]} "
                   f"age_days={days_since(sn['publishedAt']):.0f} channel='{sn['channelTitle']}' "
                   f"subs_now={ch.get('subscriberCount', 'hidden')}")
        con.execute("UPDATE seed_cases SET verified_at=?, verification=? WHERE video_id=?", (now, res, vid))
        out.append((vid, label, rep, res))
    con.commit()
    return out
