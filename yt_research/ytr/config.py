"""Settings. All values can be overridden by environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(os.environ.get("YTR_DB", ROOT / "data" / "ytr.sqlite"))
REPORT_DIR = Path(os.environ.get("YTR_REPORT_DIR", ROOT / "reports"))

# Research conditions from the brief
WINDOW_DAYS = int(os.environ.get("YTR_WINDOW_DAYS", 90))       # published within N days
MIN_VIEWS = int(os.environ.get("YTR_MIN_VIEWS", 50_000))        # "hit" threshold
MUSIC_CATEGORY_ID = "10"                                        # excluded from research

# YouTube Data API v3 default quota is 10,000 units/day, reset at midnight Pacific.
DAILY_QUOTA = int(os.environ.get("YTR_DAILY_QUOTA", 10_000))
RUN_BUDGET = int(os.environ.get("YTR_RUN_BUDGET", 9_000))       # leave ~1,000 units headroom
QUOTA_TZ = "America/Los_Angeles"

# Official costs (units) per call. https://developers.google.com/youtube/v3/determine_quota_cost
COST = {"search": 100, "videos": 1, "channels": 1, "playlistItems": 1, "videoCategories": 1}

# Cycle tuning
SEARCHES_PER_RUN = int(os.environ.get("YTR_SEARCHES_PER_RUN", 40))
CHANNEL_AUDIT_MAX_PAGES = 4          # 4 x 50 uploads per channel max
CHANNEL_REAUDIT_DAYS = 7
REFRESH_MAX_VIDEOS = 2_500           # 50 per unit -> <=50 units

# Format classification. The API exposes no "isShort" flag; duration is a proxy.
SHORT_MAX_S = 60          # <=60s: very likely Shorts
AMBIGUOUS_MAX_S = 180     # 61-180s: could be Shorts (3-min Shorts allowed since Oct 2024)

# Channel "replicability" thresholds (tunable; documented in README)
REPL_MIN_UPLOADS = 5
REPL_MIN_MEDIAN = 20_000
REPL_MIN_HIT_SHARE = 0.30
NEW_CHANNEL_DAYS = 365
SMALL_CHANNEL_SUBS = 100_000

ANTHROPIC_MODEL = os.environ.get("YTR_CLAUDE_MODEL", "claude-opus-5-5")

# Survivorship-bias control: a share of searches use order=date (newest uploads that are
# already 14-60 days old) instead of order=viewCount, so that failed / average uploads in a
# genre are observed too, not only winners.
DATE_SAMPLE_SHARE = float(os.environ.get("YTR_DATE_SAMPLE_SHARE", 0.25))
DATE_SAMPLE_MIN_AGE_DAYS = 14
DATE_SAMPLE_MAX_AGE_DAYS = 60

# Genres to cover first (owner's current interest). Others follow, least-covered first.
PRIORITY_GENRES = ("mens_sexual_health", "relationships_dating", "sex_trivia_edu", "grooming_men",
                   "midlife_men", "aga_hair", "sleep_health", "side_income", "asset_building")
