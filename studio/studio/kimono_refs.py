"""Reference survey of real kimono/hakama/furisode photos (needs GEMINI_API_KEY; run in Actions - the sandbox cannot reach the hosts).
Source: Wikimedia Commons (freely licensed files only; metadata + licence recorded; images are NOT stored, only analysis results).
Pipeline: Commons search API -> thumbnails (640 px) -> Gemini vision with a fixed question form (JSON) -> aggregated stats.
Usage: python -m studio.kimono_refs N     (N = number of images to analyse; default 60)
Output: work/gemini_live/kimono_refs.jsonl + kimono_refs_summary.json  (published to the studio-samples branch by the workflow)
Polite to Wikimedia: custom User-Agent without personal data, small thread count, short delay. Hard token budget stops the run."""
import base64
import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from . import gemini

API = "https://commons.wikimedia.org/w/api.php"
UA = "kimono-reference-survey/0.1 (non-commercial research; stores analysis results only)"
QUERIES = ["furisode obi back", "kimono obi from behind", "hakama back view women", "obi knot back kimono", "japanese woman kimono rear view", "obi musubi back view",
           "hakama graduation", "women hakama back", "furisode", "furisode back obi", "seijin shiki furisode", "coming of age day kimono",
           "kimono back view obi", "obi musubi", "bunko musubi", "fukura suzume", "tateya musubi", "graduation ceremony Japan hakama", "kitsuke",
           "Japanese women kimono standing back", "hanhaba obi", "nishaku sode", "university graduation Japan kimono hakama"]
MODEL = "gemini-3.8-flash"
TOKEN_BUDGET = 4_500_000   # input+output tokens; hard stop

FORM = """You are annotating a photo for a structural survey of Japanese women's formal dress. Answer ONLY with JSON using exactly these keys:
{"relevant": true/false  (a real person visibly wearing kimono/furisode/hakama; false for objects, men, children-only, drawings, museum items, crowds without detail),
 "garment": "furisode"|"hakama_female"|"hakama_male"|"kimono_other"|"yukata"|"other",
 "view": "back"|"front"|"side"|"closeup_back"|"other",
 "obi_knot": "bunko_ribbon"|"two_tier_bunko"|"fukura_suzume"|"tateya"|"taiko"|"hanhaba_ribbon_on_hakama"|"other"|"not_visible",
 "wings_count": integer or null (visible loops/wings of the obi knot),
 "symmetrical": true/false/null,
 "obi_age_visible": true/false/null,
 "obi_jime_visible": true/false/null,
 "hakama_back_board_visible": true/false/null,
 "hakama_back_tie_bow_visible": true/false/null,
 "back_tie_bow_off_center": true/false/null,
 "back_tie_tails_unequal": true/false/null,
 "ribbon_above_back_board": true/false/null,
 "back_pleats_visible": integer or null,
 "face_visible": true/false,
 "palette": "gray_muted"|"pastel"|"bright_colorful"|"dark"|"mixed"}
No prose."""


def search_files(n):
    s = requests.Session(); s.headers["User-Agent"] = UA
    seen, out = set(), []
    for q in QUERIES:
        cont = {}
        while len(out) < n * 2:   # collect extra: many will be irrelevant
            p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 50,
                 "prop": "imageinfo", "iiprop": "url|mime|extmetadata", "iiurlwidth": 640, **cont}
            r = s.get(API, params=p, timeout=60)
            if r.status_code != 200:
                break
            j = r.json()
            for pg in (j.get("query", {}).get("pages", {}) or {}).values():
                ii = (pg.get("imageinfo") or [{}])[0]
                if pg["title"] in seen or ii.get("mime") not in ("image/jpeg", "image/png") or not ii.get("thumburl"):
                    continue
                seen.add(pg["title"])
                em = ii.get("extmetadata", {})
                out.append(dict(title=pg["title"], thumb=ii["thumburl"], page=ii.get("descriptionurl"), query=q,
                                license=(em.get("LicenseShortName") or {}).get("value"), artist_present=bool(em.get("Artist"))))
            if "continue" not in j or len(out) >= n * 2:
                break
            cont = j["continue"]; time.sleep(0.5)
        time.sleep(0.5)
    return out[: n * 2]


def analyse(item, sess, lock, usage):
    if usage["tokens"] > TOKEN_BUDGET:
        return None
    try:
        r = sess.get(item["thumb"], timeout=60, headers={"User-Agent": UA})
        if r.status_code != 200 or len(r.content) < 3000:
            return None
        body = {"contents": [{"parts": [{"text": FORM}, {"inlineData": {"mimeType": r.headers.get("content-type", "image/jpeg").split(";")[0], "data": base64.b64encode(r.content).decode()}}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        try:
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}   # no hidden reasoning tokens: cheaper
            resp = gemini.generate_content(MODEL, body)
        except gemini.GeminiError:
            body["generationConfig"].pop("thinkingConfig", None)
            resp = gemini.generate_content(MODEL, body)
        u = gemini.usage(resp)
        with lock:
            usage["tokens"] += u["input_tokens"] + u["output_tokens"] + u["thought_tokens"]; usage["in"] += u["input_tokens"]; usage["out"] += u["output_tokens"] + u["thought_tokens"]
        data = json.loads(gemini.text_of(resp))
        if isinstance(data, list):
            data = data[0]
        return {**{k: item[k] for k in ("title", "page", "license")}, **data}
    except Exception as e:  # noqa: BLE001
        with lock:
            usage["errors"] += 1
        print("ERR", type(e).__name__, str(e)[:120], flush=True)
        return None


def summarize(rows):
    rel = [r for r in rows if r.get("relevant")]
    def cnt(key, subset):
        return dict(Counter(str(r.get(key)) for r in subset).most_common())
    hk = [r for r in rel if r.get("garment") == "hakama_female"]
    fu = [r for r in rel if r.get("garment") == "furisode"]
    back_hk = [r for r in hk if r.get("view") in ("back", "closeup_back")]
    back_fu = [r for r in fu if r.get("view") in ("back", "closeup_back")]
    return dict(analysed=len(rows), relevant=len(rel), garments=cnt("garment", rel), views=cnt("view", rel),
                hakama_female=dict(n=len(hk), back_views=len(back_hk), obi_knot=cnt("obi_knot", back_hk), wings=cnt("wings_count", back_hk),
                                   back_board=cnt("hakama_back_board_visible", back_hk), tie_bow=cnt("hakama_back_tie_bow_visible", back_hk),
                                   bow_off_center=cnt("back_tie_bow_off_center", back_hk), tails_unequal=cnt("back_tie_tails_unequal", back_hk),
                                   ribbon_above_board=cnt("ribbon_above_back_board", back_hk), pleats=cnt("back_pleats_visible", back_hk), palette=cnt("palette", hk)),
                furisode=dict(n=len(fu), back_views=len(back_fu), obi_knot=cnt("obi_knot", back_fu), wings=cnt("wings_count", back_fu),
                              symmetrical=cnt("symmetrical", back_fu), obi_age=cnt("obi_age_visible", back_fu), obi_jime=cnt("obi_jime_visible", back_fu), palette=cnt("palette", fu)))


def main(n=60):
    out = Path(__file__).resolve().parent.parent / "work" / "gemini_live"
    out.mkdir(parents=True, exist_ok=True)
    items = search_files(n)
    print("candidates", len(items), flush=True)
    usage = dict(tokens=0, **{"in": 0, "out": 0, "errors": 0}); lock = threading.Lock()
    sess = requests.Session()
    rows = []
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(lambda it: analyse(it, sess, lock, usage), items):
            if res:
                rows.append(res)
            if len(rows) >= n:
                break
    rows = rows[:n]
    (out / "kimono_refs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    summ = summarize(rows); summ["usage"] = usage; summ["model"] = MODEL
    (out / "kimono_refs_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), "utf-8")
    print("USAGE", usage, flush=True)
    print("SUMMARY", json.dumps(summ, ensure_ascii=False)[:3500], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 60))
