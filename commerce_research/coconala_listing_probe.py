"""Read PUBLIC Coconala listing pages (robots.txt allows /services/ID), low volume, and extract price + sales evidence.
Fields (all shown publicly on the page): title, price (first 'price' value in the page data, may be an option price -> treat as indicative), 販売実績(this listing), 評価(avg,count), 総販売実績(seller total).
Treat sales/ratings as: evidence level = 'platform-displayed counts' (not audited revenue). Usage: python3 coconala_listing_probe.py OUT.csv ID [ID...]"""
import csv, html, re, subprocess, sys, time
def probe(i):
    p = subprocess.run(["curl", "-sS", "-m", "25", "-L", "-A", "Mozilla/5.0 (non-commercial research; low volume)", f"https://coconala.com/services/{i}"], capture_output=True, text=True)
    t = p.stdout
    if len(t) < 5000: return dict(id=i, status="fetch_failed")
    title = html.unescape(re.sub(r"\s*\|\s*ココナラ.*$", "", (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1])).strip()
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
    prices = [int(x) for x in re.findall(r'"price"\s*:\s*(\d{3,7})', t)]
    m = re.search(r"評価\s*([\d.]+|-)\s*(?:\((\d[\d,]*)\))?\s*販売実績\s*(\d[\d,]*)\s*件", txt)
    tot = re.search(r"総販売実績[：:]\s*(\d[\d,]*)\s*件", txt)
    closed = "受付終了" in txt[:1500]
    n = lambda s: int(s.replace(",", "")) if s else None
    return dict(id=i, status="ok", title=title[:90], price_first=prices[0] if prices else None, price_min=min(prices) if prices else None, rating=(m.group(1) if m else None), rating_count=n(m.group(2)) if m else None,
                sales_listing=n(m.group(3)) if m else None, sales_seller_total=n(tot.group(1)) if tot else None, closed=closed)
if __name__ == "__main__":
    out, ids = sys.argv[1], sys.argv[2:]
    rows = []
    for i in ids:
        rows.append(probe(i)); time.sleep(3)
    keys = ["id", "status", "title", "price_first", "price_min", "rating", "rating_count", "sales_listing", "sales_seller_total", "closed"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); [w.writerow({k: r.get(k) for k in keys}) for r in rows]
    print(len(rows), "rows ->", out)
