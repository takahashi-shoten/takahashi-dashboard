import re
from datetime import datetime, timezone, timedelta

_DUR = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def days_since(s: str, now: datetime | None = None) -> float:
    now = now or utcnow()
    return max((now - parse_iso(s)).total_seconds() / 86400, 1 / 24)


def parse_duration(s: str | None) -> int | None:
    """ISO-8601 duration (PT1H2M3S) -> seconds."""
    if not s:
        return None
    m = _DUR.match(s)
    if not m:
        return None
    d, h, mi, se = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def format_class(duration_s: int | None) -> str:
    from .config import SHORT_MAX_S, AMBIGUOUS_MAX_S
    if duration_s is None:
        return "unknown"
    if duration_s == 0:
        return "live_or_upcoming"
    if duration_s <= SHORT_MAX_S:
        return "short_likely"
    if duration_s <= AMBIGUOUS_MAX_S:
        return "ambiguous"
    return "long"


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def window_start(days: int, now: datetime | None = None) -> datetime:
    return (now or utcnow()) - timedelta(days=days)
