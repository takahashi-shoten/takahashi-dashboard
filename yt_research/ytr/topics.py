"""Research topics: seeds, scheduling (explore/exploit) and data-driven expansion."""
import json
import math
import re
from collections import Counter

from .util import iso, utcnow, parse_iso

# (genre, lang, region, query). Music is excluded by design.
# Broad on purpose: the past research was limited to ~5 genres; these are starting points
# that the scheduler down-weights when they stop yielding new evidence.
SEEDS = [
    # history / civilisation / maps
    ("history", "en", "US", "ancient history documentary"), ("history", "en", "US", "how people lived in medieval times"),
    ("history", "ja", "JP", "歴史 解説"), ("history", "ja", "JP", "古代文明 謎"),
    ("history", "es", "MX", "historia documental"), ("history", "pt", "BR", "história documentário"),
    ("maps_geo", "en", "US", "geography explained map"), ("maps_geo", "ja", "JP", "地理 地図 解説"),
    ("infrastructure", "en", "US", "megaproject engineering explained"), ("infrastructure", "ja", "JP", "インフラ 巨大建造物"),
    # science / education
    ("science", "en", "US", "science explained animation"), ("science", "ja", "JP", "科学 解説 アニメーション"),
    ("science", "hi", "IN", "science facts hindi"), ("space", "en", "US", "space documentary universe"),
    ("space", "ja", "JP", "宇宙 解説"), ("biology_nature", "en", "US", "animal behavior documentary"),
    ("biology_nature", "ja", "JP", "動物 生態 解説"), ("psychology", "en", "US", "psychology explained"),
    ("psychology", "ja", "JP", "心理学 解説"), ("economics", "en", "US", "economics explained country"),
    ("economics", "ja", "JP", "経済 解説 図解"), ("math_logic", "en", "US", "math puzzle explained"),
    # fiction / AI film / drama
    ("scifi_story", "en", "US", "sci-fi short film"), ("scifi_story", "en", "US", "what if scenario future"),
    ("scifi_story", "ja", "JP", "SF 短編 アニメ"), ("ai_film", "en", "US", "AI short film"),
    ("ai_film", "ja", "JP", "AI 動画 ショートフィルム"), ("drama_story", "en", "US", "animated story drama"),
    ("drama_story", "ja", "JP", "スカッと 漫画 動画"), ("drama_story", "en", "US", "reddit stories"),
    ("drama_story", "es", "MX", "historias animadas"), ("drama_story", "pt", "BR", "histórias animadas"),
    ("horror_mystery", "en", "US", "unsolved mysteries documentary"), ("horror_mystery", "ja", "JP", "未解決事件 解説"),
    ("horror_mystery", "en", "US", "scary stories animated"),
    # cozy / slice of life
    ("cozy_life", "en", "US", "cozy village life animation"), ("cozy_life", "en", "US", "rural life cooking countryside"),
    ("cozy_life", "ja", "JP", "田舎暮らし 日常"), ("cozy_life", "zh", "TW", "鄉村生活"),
    # practical / how-to / money
    ("diy_craft", "en", "US", "restoration rusty"), ("diy_craft", "en", "US", "build tiny house diy"),
    ("cooking", "en", "US", "street food"), ("cooking", "ja", "JP", "料理 簡単 レシピ"),
    ("personal_finance", "en", "US", "personal finance explained"), ("personal_finance", "ja", "JP", "お金 節約 解説"),
    ("tech_explain", "en", "US", "how it works technology explained"), ("tech_explain", "ja", "JP", "仕組み 解説 テクノロジー"),
    ("ai_news_tools", "en", "US", "AI tools tutorial"), ("ai_news_tools", "ja", "JP", "AI ツール 使い方"),
    ("language_learning", "en", "US", "learn english conversation"), ("language_learning", "ja", "JP", "英会話 聞き流し"),
    ("health_body", "en", "US", "what happens to your body if"), ("health_body", "ja", "JP", "体 健康 雑学"),
    # culture / travel / misc
    ("travel_culture", "en", "US", "why is this country"), ("travel_culture", "ja", "JP", "海外の反応"),
    ("true_crime", "en", "US", "true crime documentary"), ("aviation_military", "en", "US", "military history explained"),
    ("aviation_military", "en", "US", "aviation disaster explained"), ("cars_machines", "en", "US", "machine how it's made"),
    ("kids_edu", "en", "US", "kids learning video"), ("comparison_data", "en", "US", "size comparison 3d"),
    ("comparison_data", "en", "US", "data visualization comparison"), ("philosophy", "en", "US", "philosophy explained stoicism"),
    ("religion_myth", "en", "US", "mythology explained"), ("religion_myth", "ja", "JP", "神話 解説"),
    ("sports_story", "en", "US", "sports story documentary"), ("gaming_lore", "en", "US", "game lore explained"),
    ("relaxing_visual", "en", "US", "relaxing nature 4k no music"), ("asmr_process", "en", "US", "satisfying factory process"),
    ("indonesia_misc", "id", "ID", "kisah nyata animasi"), ("korea_misc", "ko", "KR", "역사 이야기"),
    ("de_misc", "de", "DE", "dokumentation geschichte"), ("fr_misc", "fr", "FR", "documentaire histoire"),
    # adult-adjacent, non-explicit demand (men's health, relationships, dating). Platform-compliant themes only.
    ("mens_sexual_health", "ja", "JP", "ED 原因 対策 解説"), ("mens_sexual_health", "ja", "JP", "精力 テストステロン 男性ホルモン"),
    ("mens_sexual_health", "en", "US", "testosterone low symptoms explained"), ("mens_sexual_health", "en", "US", "men's sexual health doctor explains"),
    ("relationships_dating", "ja", "JP", "婚活 中年 男性"), ("relationships_dating", "ja", "JP", "恋愛 モテる 40代"),
    ("relationships_dating", "ja", "JP", "セックスレス 夫婦 解説"), ("relationships_dating", "en", "US", "dating over 40 men advice"),
    ("relationships_dating", "en", "US", "relationship psychology attraction explained"), ("grooming_men", "ja", "JP", "40代 男 清潔感 身だしなみ"),
    ("grooming_men", "en", "US", "men over 40 grooming style"), ("midlife_men", "ja", "JP", "中年 男性 孤独 趣味"),
    ("aga_hair", "ja", "JP", "薄毛 AGA 対策"), ("sleep_health", "ja", "JP", "睡眠 改善 中年"),
    ("side_income", "ja", "JP", "副業 おすすめ 会社員"), ("asset_building", "ja", "JP", "新NISA 資産形成 40代"),
    # "hee~" trivia about sex/body/culture, tasteful and non-explicit (history, biology, psychology, myth-busting)
    ("sex_trivia_edu", "ja", "JP", "性の雑学 歴史 文化"), ("sex_trivia_edu", "ja", "JP", "江戸時代 性文化 解説"),
    ("sex_trivia_edu", "ja", "JP", "人体 不思議 雑学 男性"), ("sex_trivia_edu", "ja", "JP", "恋愛 心理学 雑学"),
    ("sex_trivia_edu", "en", "US", "weird facts about the human body"), ("sex_trivia_edu", "en", "US", "history of sex culture explained"),
    ("sex_trivia_edu", "en", "US", "animal mating behavior facts"), ("sex_trivia_edu", "en", "US", "sex myths debunked doctor"),
    # carried over verbatim from the legacy youtube_research_prototype QUERIES (for continuity)
    ("science", "ja", "JP", "科学 解説"), ("trivia", "ja", "JP", "雑学 なぜ"), ("drama_story", "ja", "JP", "短編ドラマ"),
    ("horror_mystery", "ja", "JP", "都市伝説 考察"), ("ai_film", "ja", "JP", "AI アニメ"), ("economics", "ja", "JP", "経済 解説"),
    ("cooking", "ja", "JP", "料理 科学"), ("gaming_lore", "ja", "JP", "ゲーム 解説"), ("biology_nature", "ja", "JP", "動物 生態"),
    ("science", "en", "US", "science explained"), ("scifi_story", "en", "US", "short film story"),
    ("history", "en", "US", "history animation"), ("tech_explain", "en", "US", "future technology"),
    ("horror_mystery", "en", "US", "mystery documentary"), ("maps_geo", "en", "US", "world maps explained"),
    ("infrastructure", "en", "US", "engineering explained"), ("biology_nature", "en", "US", "wildlife documentary"),
    ("ai_film", "en", "US", "AI cinematic story"),
]

MIN_RERUN_DAYS = 3


def ensure_seeds(con):
    now = iso(utcnow())
    for genre, lang, region, q in SEEDS:
        con.execute("INSERT OR IGNORE INTO topics(query, lang, region, genre, source, created_at) VALUES(?,?,?,?,?,?)",
                    (q, lang, region, genre, "seed", now))
    con.commit()


def add_topic(con, query, lang, region, genre, source, notes=None) -> bool:
    cur = con.execute(
        "INSERT OR IGNORE INTO topics(query, lang, region, genre, source, created_at, notes) VALUES(?,?,?,?,?,?,?)",
        (query.strip(), lang, region, genre, source, iso(utcnow()), notes))
    con.commit()
    return cur.rowcount > 0


def select_topics(con, n: int, now=None):
    """Never-run topics first (spread across genres), then UCB1 on yield_score."""
    now = now or utcnow()
    rows = con.execute("SELECT * FROM topics WHERE status='active'").fetchall()
    total_runs = sum(r["runs"] for r in rows) + 1
    fresh, scored = [], []
    for r in rows:
        if r["runs"] == 0:
            fresh.append(r)
            continue
        if r["last_run_at"] and (now - parse_iso(r["last_run_at"])).days < MIN_RERUN_DAYS:
            continue
        ucb = (r["yield_score"] or 0) + 0.5 * math.sqrt(math.log(total_runs) / r["runs"])
        scored.append((ucb, r))
    # round-robin genres among fresh topics so one genre cannot eat the budget
    from . import config
    searched = {r[0]: r[1] for r in con.execute("SELECT genre, SUM(runs) FROM topics GROUP BY genre")}
    by_genre = {}
    for r in sorted(fresh, key=lambda r: r["topic_id"]):
        by_genre.setdefault(r["genre"], []).append(r)
    # priority genres first, then the genres searched least so far -> every genre reaches the
    # support threshold (8 audited channels) as early as the quota allows
    genre_order = sorted(by_genre, key=lambda g: (g not in config.PRIORITY_GENRES, searched.get(g) or 0, g))
    ordered = []
    while any(by_genre.values()):
        for g in genre_order:
            if by_genre[g]:
                ordered.append(by_genre[g].pop(0))
    ordered += [r for _, r in sorted(scored, key=lambda x: -x[0])]
    return ordered[:n]


def update_yield(con, topic_id, new_hit_channels, new_hits, result_count, now_iso):
    """EMA of evidence yield. New hit *channels* matter more than repeat hits."""
    y = 0.0 if result_count == 0 else min(1.0, new_hit_channels / 5 + new_hits / 50)
    r = con.execute("SELECT yield_score, runs FROM topics WHERE topic_id=?", (topic_id,)).fetchone()
    prev = r["yield_score"]
    new = y if prev is None else 0.6 * prev + 0.4 * y
    status = "active"
    if r["runs"] + 1 >= 4 and new < 0.02:
        status = "paused"   # stops wasting 100-unit searches on dead topics
    con.execute("UPDATE topics SET yield_score=?, runs=runs+1, last_run_at=?, status=? WHERE topic_id=?",
                (new, now_iso, status, topic_id))


_WORD = re.compile(r"[#\w぀-ヿ一-鿿]+", re.UNICODE)
_STOP = set("the a an of in to and for is on with how why what you your this that are from by at it be".split())


def expand_from_hits(con, max_new=5):
    """Propose new queries from tags of hit videos on *replicable* channels (data-driven, no LLM)."""
    rows = con.execute("""
      SELECT t.genre, t.lang, t.region, v.tags_json FROM discoveries d
      JOIN topics t ON t.topic_id=d.topic_id JOIN videos v ON v.video_id=d.video_id
      JOIN channel_metrics m ON m.channel_id=v.channel_id
      WHERE m.replicable=1 AND v.category_id != '10'""").fetchall()
    counts = Counter()
    meta = {}
    for r in rows:
        for tag in json.loads(r["tags_json"] or "[]")[:15]:
            tag = tag.strip().lower()
            if 3 <= len(tag) <= 40 and tag not in _STOP:
                counts[(tag, r["lang"], r["region"])] += 1
                meta[(tag, r["lang"], r["region"])] = r["genre"]
    added = 0
    for (tag, lang, region), c in counts.most_common(50):
        if c < 3:
            break
        if add_topic(con, tag, lang, region, meta[(tag, lang, region)], "expansion", f"tag freq={c}"):
            added += 1
        if added >= max_new:
            break
    return added


def select_date_sample_topics(con, n):
    """Topics for unbiased-ish sampling: least recently date-sampled first, spread over genres."""
    rows = con.execute("""SELECT * FROM topics WHERE status IN ('active','paused')
                          ORDER BY (date_sampled_at IS NOT NULL), date_sampled_at, topic_id""").fetchall()
    seen, out = set(), []
    for r in rows:                      # one per genre first
        if r["genre"] not in seen:
            seen.add(r["genre"]); out.append(r)
    out += [r for r in rows if r not in out]
    return out[:n]
