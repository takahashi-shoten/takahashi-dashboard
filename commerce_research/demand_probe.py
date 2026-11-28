"""Global-demand public-data probe (stdlib only). Runs on a GitHub Actions runner (open network).
1) reachability of candidate public sources (status/bytes only, one GET each, polite UA)
2) Apple official RSS top-paid apps (many countries) + iTunes Lookup (price, rating count = public display value)
3) Steam store top sellers (public store API) -> price, reviews
Writes JSON/CSV to OUT dir. Observed public values only; no scraping of logged-in pages. Usage: python3 demand_probe.py OUT"""
import json, sys, time, csv, urllib.request, urllib.error, os, datetime
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (compatible; demand-research-probe; low-rate)"
NOW = datetime.datetime.utcnow().isoformat() + "Z"
def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()[:200]
# 1 reachability
hosts = {
 "apple_rss": "https://rss.applemarketingtools.com/api/v2/jp/apps/top-paid/10/apps.json",
 "itunes_lookup": "https://itunes.apple.com/lookup?id=284882215&country=jp",
 "steam_featured": "https://store.steampowered.com/api/featuredcategories?cc=jp",
 "steam_appdetails": "https://store.steampowered.com/api/appdetails?appids=730&cc=jp",
 "webrobots_ks": "https://webrobots.io/kickstarter-datasets/",
 "gumroad_discover": "https://gumroad.com/discover",
 "booth_home": "https://booth.pm/ja",
 "itch_topsellers": "https://itch.io/games/top-sellers",
 "udemy_api": "https://www.udemy.com/api-2.0/courses/?page_size=2",
 "producthunt": "https://www.producthunt.com/",
 "etsy": "https://www.etsy.com/",
 "note_com": "https://note.com/",
 "hn_api": "https://hacker-news.firebaseio.com/v0/topstories.json",
 "reddit_json": "https://www.reddit.com/r/Entrepreneur/top.json?limit=2&t=week",
 "gtrends_rss_jp": "https://trends.google.com/trending/rss?geo=JP",
 "wiki_pageviews": "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/ja.wikipedia/all-access/2026/11/27",
 "hf_amazon_reviews": "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/README.md",
 "estat": "https://www.e-stat.go.jp/",
 "worldbank_api": "https://api.worldbank.org/v2/country/JP/indicator/NY.GDP.PCAP.CD?format=json&per_page=2",
 "chrome_webstore": "https://chromewebstore.google.com/",
 "kindle_jp_ranking": "https://www.amazon.co.jp/gp/bestsellers/digital-text",
 "fiverr": "https://www.fiverr.com/",
 "lancers": "https://www.lancers.jp/",
}
reach = {}
for k, u in hosts.items():
    s, b = get(u); reach[k] = {"url": u, "status": s, "bytes": len(b)}; time.sleep(1)
json.dump({"observed_at": NOW, "reach": reach}, open(f"{OUT}/reachability.json", "w"), ensure_ascii=False, indent=1)
# 2 apple top paid
countries = ["jp","us","gb","de","fr","kr","tw","br","in","id","th","vn","mx","au","ca","es","it"]
apps = {}
for c in countries:
    s, b = get(f"https://rss.applemarketingtools.com/api/v2/{c}/apps/top-paid/100/apps.json")
    if s != 200: print("rss", c, s); continue
    for i, a in enumerate(json.loads(b)["feed"]["results"], 1):
        apps.setdefault(a["id"], {"id": a["id"], "name": a["name"], "ranks": {}})["ranks"][c] = i
    time.sleep(1)
print("unique apps", len(apps))
rows = []
ids = list(apps)
for c in countries:
    sub = [i for i in ids if c in apps[i]["ranks"]]
    for j in range(0, len(sub), 100):
        s, b = get(f"https://itunes.apple.com/lookup?id={','.join(sub[j:j+100])}&country={c}")
        if s != 200: print("lookup", c, s); continue
        for r in json.loads(b).get("results", []):
            rows.append({"country": c, "rank": apps[str(r['trackId'])]["ranks"][c], "id": r["trackId"], "name": r.get("trackName"),
              "genre": r.get("primaryGenreName"), "price": r.get("price"), "currency": r.get("currency"),
              "rating_avg": r.get("averageUserRating"), "rating_count": r.get("userRatingCount"), "seller": r.get("sellerName"),
              "released": (r.get("releaseDate") or "")[:10], "updated": (r.get("currentVersionReleaseDate") or "")[:10], "observed_at": NOW})
        time.sleep(1)
with open(f"{OUT}/apple_top_paid.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["none"]); w.writeheader(); w.writerows(rows)
print("apple rows", len(rows))
# 3 steam
st = []
for cc in ["jp","us"]:
    s, b = get(f"https://store.steampowered.com/api/featuredcategories?cc={cc}")
    if s == 200:
        d = json.loads(b)
        for it in (d.get("top_sellers") or {}).get("items", []):
            st.append({"cc": cc, "id": it.get("id"), "name": it.get("name"), "final_price": it.get("final_price"), "currency": it.get("currency"), "discount": it.get("discount_percent"), "observed_at": NOW})
    else: print("steam", cc, s)
json.dump(st, open(f"{OUT}/steam_top_sellers.json", "w"), ensure_ascii=False, indent=1)
print("steam", len(st))
